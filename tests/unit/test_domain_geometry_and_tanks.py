"""Tests du modèle de domaine : interpolation, géométrie, profil et réservoirs."""

from __future__ import annotations

import math

import pytest

from hydro_shared.errors import ProfileError, StrappingTableError

from hydro_domain.enums import EquipmentStatus
from hydro_domain.geometry import (
    ElevationProfile,
    Fitting,
    PipeSegment,
    ProfilePoint,
    validate_segment_chain,
)
from hydro_domain.interpolation import (
    ExtrapolationPolicy,
    InterpolationKind,
    MonotoneTable,
)
from hydro_domain.tanks import StrappingTable, Tank, TankLevels


class TestMonotoneTable:
    def test_interpolation_lineaire(self):
        table = MonotoneTable([0.0, 10.0], [0.0, 100.0])
        assert table(5.0) == pytest.approx(50.0)

    def test_abscisses_non_croissantes_rejetees(self):
        with pytest.raises(Exception, match="strictement croissantes"):
            MonotoneTable([0.0, 5.0, 3.0], [0.0, 1.0, 2.0])

    def test_extrapolation_signalee(self):
        table = MonotoneTable([0.0, 10.0], [0.0, 100.0])
        evaluation = table.evaluate(15.0)
        assert evaluation.extrapolated
        assert evaluation.value == pytest.approx(150.0)
        assert evaluation.detail is not None

    def test_extrapolation_clamp(self):
        table = MonotoneTable(
            [0.0, 10.0], [0.0, 100.0], extrapolation=ExtrapolationPolicy.CLAMP
        )
        evaluation = table.evaluate(15.0)
        assert evaluation.extrapolated
        assert evaluation.value == pytest.approx(100.0)

    def test_extrapolation_interdite(self):
        table = MonotoneTable(
            [0.0, 10.0], [0.0, 100.0], extrapolation=ExtrapolationPolicy.FORBID
        )
        with pytest.raises(Exception, match="hors du domaine"):
            table.evaluate(15.0)

    def test_inversion_exacte_aux_noeuds(self):
        table = MonotoneTable([0.0, 1.0, 2.0], [0.0, 3.0, 10.0])
        for x, y in zip(table.x, table.y, strict=True):
            assert table.inverse(y).value == pytest.approx(x, abs=1e-12)

    def test_inversion_refusee_si_non_monotone(self):
        table = MonotoneTable([0.0, 1.0, 2.0], [0.0, 5.0, 1.0])
        assert not table.is_invertible
        with pytest.raises(Exception, match="pas de solution unique"):
            table.inverse(3.0)

    def test_palier_empeche_inversion(self):
        """Une table monotone au sens large comporte un palier : antécédent non unique."""
        table = MonotoneTable([0.0, 1.0, 2.0], [0.0, 5.0, 5.0])
        assert not table.is_invertible

    def test_pchip_preserve_la_monotonie(self):
        table = MonotoneTable(
            [0.0, 1.0, 2.0, 3.0], [10.0, 8.0, 5.0, 1.0], kind=InterpolationKind.PCHIP
        )
        values = [table(x / 10.0) for x in range(0, 31)]
        assert all(b <= a + 1e-12 for a, b in zip(values, values[1:], strict=False))

    def test_derivee_lineaire(self):
        table = MonotoneTable([0.0, 10.0], [0.0, 100.0])
        assert table.derivative(5.0) == pytest.approx(10.0)


class TestPipeSegment:
    def _segment(self, **kwargs) -> PipeSegment:
        defaults = {
            "id": "T1",
            "sequence": 1,
            "length_m": 1000.0,
            "inner_diameter_m": 0.5,
            "roughness_m": 4.5e-5,
        }
        return PipeSegment(**{**defaults, **kwargs})

    def test_section_et_volume(self):
        segment = self._segment()
        assert segment.area_m2 == pytest.approx(math.pi * 0.25 / 4.0)
        assert segment.volume_m3 == pytest.approx(segment.area_m2 * 1000.0)

    def test_vitesse(self):
        segment = self._segment()
        assert segment.velocity(segment.area_m2) == pytest.approx(1.0)

    def test_rugosite_relative(self):
        assert self._segment().relative_roughness == pytest.approx(4.5e-5 / 0.5)

    @pytest.mark.parametrize(
        ("champ", "valeur"),
        [("length_m", 0.0), ("length_m", -1.0), ("inner_diameter_m", 0.0), ("roughness_m", -1e-6)],
    )
    def test_dimensions_non_positives_rejetees(self, champ, valeur):
        """Règle DQ-002 : diamètre, longueur ou capacité non positive est bloquant."""
        with pytest.raises(ValueError):
            self._segment(**{champ: valeur})

    def test_diametre_exterieur_incoherent_rejete(self):
        with pytest.raises(ValueError, match="diamètre extérieur"):
            self._segment(outer_diameter_m=0.4)

    def test_somme_des_k_des_accessoires(self):
        segment = self._segment(
            fittings=(
                Fitting(id="V1", kind="vanne", k_coefficient=0.2, quantity=2),
                Fitting(id="C1", kind="coude", k_coefficient=0.3),
            )
        )
        assert segment.total_fitting_k() == pytest.approx(0.7)

    def test_accessoire_hors_service_ne_compte_pas(self):
        segment = self._segment(
            fittings=(
                Fitting(
                    id="V1",
                    kind="vanne",
                    k_coefficient=0.5,
                    status=EquipmentStatus.UNAVAILABLE,
                ),
            )
        )
        assert segment.total_fitting_k() == pytest.approx(0.0)

    def test_vanne_partiellement_fermee_augmente_la_perte(self):
        """Scénario obligatoire « vanne partiellement fermée » (§ 4.8)."""
        ouverte = Fitting(id="V", kind="vanne", k_coefficient=0.5, opening_ratio=1.0)
        demi = Fitting(id="V", kind="vanne", k_coefficient=0.5, opening_ratio=0.5)
        assert demi.effective_k() == pytest.approx(4.0 * ouverte.effective_k())

    def test_vanne_fermee_bloque(self):
        assert Fitting(id="V", kind="vanne", k_coefficient=0.5, opening_ratio=0.0).effective_k() == math.inf


class TestChaineDeTroncons:
    def test_chaine_continue_valide(self):
        segments = [
            PipeSegment(
                id=f"T{i}",
                sequence=i,
                length_m=1000.0,
                inner_diameter_m=0.5,
                roughness_m=4.5e-5,
                start_chainage_m=(i - 1) * 1000.0,
            )
            for i in (1, 2, 3)
        ]
        assert validate_segment_chain(segments) == []

    def test_discontinuite_detectee(self):
        segments = [
            PipeSegment(
                id="T1",
                sequence=1,
                length_m=1000.0,
                inner_diameter_m=0.5,
                roughness_m=4.5e-5,
                start_chainage_m=0.0,
            ),
            PipeSegment(
                id="T2",
                sequence=2,
                length_m=1000.0,
                inner_diameter_m=0.5,
                roughness_m=4.5e-5,
                start_chainage_m=1500.0,
            ),
        ]
        problems = validate_segment_chain(segments)
        assert len(problems) == 1
        assert "Discontinuité" in problems[0]

    def test_identifiants_dupliques_detectes(self):
        segments = [
            PipeSegment(
                id="T1",
                sequence=i,
                length_m=1000.0,
                inner_diameter_m=0.5,
                roughness_m=4.5e-5,
                start_chainage_m=(i - 1) * 1000.0,
            )
            for i in (1, 2)
        ]
        assert any("dupliqués" in p for p in validate_segment_chain(segments))


class TestElevationProfile:
    def test_interpolation(self):
        profile = ElevationProfile.from_kilometre_pairs([(0, 100.0), (10, 200.0)])
        assert profile.elevation_at(5000.0) == pytest.approx(150.0)

    def test_hors_domaine_maintient_l_altitude_extreme(self):
        """Le maintien évite de fabriquer un relief au-delà des points levés."""
        profile = ElevationProfile.from_kilometre_pairs([(0, 100.0), (10, 200.0)])
        assert profile.elevation_at(-1000.0) == pytest.approx(100.0)
        assert profile.elevation_at(20000.0) == pytest.approx(200.0)

    def test_profil_trop_court_rejete(self):
        with pytest.raises(ProfileError):
            ElevationProfile([ProfilePoint(0.0, 100.0)])

    def test_chainages_non_croissants_rejetes(self):
        """Règle DQ-003 : profil non ordonné est bloquant."""
        with pytest.raises(ProfileError):
            ElevationProfile.from_pairs([(0.0, 100.0), (5000.0, 120.0), (3000.0, 110.0)])

    def test_denivele(self):
        profile = ElevationProfile.from_kilometre_pairs([(0, 100.0), (10, 250.0)])
        assert profile.elevation_change(0.0, 10000.0) == pytest.approx(150.0)

    def test_echantillonnage_conserve_les_points_d_origine(self):
        """Le sommet d'une côte ne doit jamais disparaître d'un ré-échantillonnage."""
        profile = ElevationProfile.from_kilometre_pairs([(0, 100.0), (3, 400.0), (10, 120.0)])
        sampled = profile.sample(5000.0)
        chainages = [p.chainage_m for p in sampled]
        assert 3000.0 in chainages
        assert 0.0 in chainages
        assert 10000.0 in chainages

    def test_detection_des_sommets(self):
        profile = ElevationProfile.from_kilometre_pairs(
            [(0, 100.0), (5, 300.0), (10, 150.0), (15, 280.0), (20, 90.0)]
        )
        assert profile.summit_chainages() == [5000.0, 15000.0]


class TestStrappingTable:
    def test_cylindre_vertical(self):
        """Cas VAL-TNK-001 : bac cylindrique, V = A·h."""
        table = StrappingTable.from_vertical_cylinder(diameter_m=20.0, height_m=12.0)
        area = math.pi * 20.0**2 / 4.0
        assert table.volume_at(6.0) == pytest.approx(area * 6.0)
        assert table.max_volume_m3 == pytest.approx(area * 12.0)

    def test_inversion_hauteur_volume(self):
        """Cas VAL-TNK-003 : monotonie et inversion h(V)."""
        table = StrappingTable.from_pairs([(0.0, 0.0), (0.5, 980.0), (1.0, 1965.0), (1.5, 2952.0)])
        assert table.height_at(1965.0) == pytest.approx(1.0)
        assert table.height_at(0.0) == pytest.approx(0.0)
        # Aller-retour sur un point intermédiaire non tabulé.
        volume = table.volume_at(0.75)
        assert table.height_at(volume) == pytest.approx(0.75)

    def test_table_non_monotone_rejetee(self):
        """Règle DQ-004 : barémage non monotone est bloquant."""
        with pytest.raises(StrappingTableError):
            StrappingTable.from_pairs([(0.0, 0.0), (1.0, 100.0), (2.0, 50.0)])

    def test_volume_negatif_rejete(self):
        with pytest.raises(StrappingTableError):
            StrappingTable.from_pairs([(0.0, -10.0), (1.0, 100.0)])

    def test_hors_table_leve_une_erreur(self):
        table = StrappingTable.from_vertical_cylinder(10.0, 5.0)
        with pytest.raises(StrappingTableError):
            table.volume_at(6.0)

    def test_derivee_donne_la_section(self):
        table = StrappingTable.from_vertical_cylinder(diameter_m=10.0, height_m=8.0)
        assert table.dvolume_dheight(4.0) == pytest.approx(math.pi * 25.0, rel=1e-9)


class TestTank:
    def _tank(self, **kwargs) -> Tank:
        defaults = {
            "id": "B1",
            "name": "Bac 1",
            "strapping": StrappingTable.from_vertical_cylinder(20.0, 12.0),
            "levels": TankLevels(minimum_m=0.5, low_m=1.0, normal_m=6.0, high_m=10.0, high_high_m=11.0),
            "current_level_m": 6.0,
        }
        return Tank(**{**defaults, **kwargs})

    def test_volumes_derives(self):
        tank = self._tank()
        area = math.pi * 100.0
        assert tank.current_volume_m3 == pytest.approx(area * 6.0)
        assert tank.available_capacity_m3 == pytest.approx(area * 5.0)
        assert tank.pumpable_volume_m3 == pytest.approx(area * 5.5)
        assert tank.usable_volume_m3 == pytest.approx(area * 10.5)

    def test_seuils_desordonnes_rejetes(self):
        with pytest.raises(StrappingTableError):
            TankLevels(minimum_m=2.0, low_m=1.0, high_high_m=10.0)

    def test_niveau_tres_haut_au_dela_du_baremage_rejete(self):
        with pytest.raises(StrappingTableError, match="dépasse la hauteur maximale"):
            self._tank(levels=TankLevels(minimum_m=0.5, high_high_m=15.0))

    def test_compatibilite_produit(self):
        """FR-TNK-005 : un bac contenant déjà un produit n'accepte que celui-ci."""
        tank = self._tank(fluid_id="gasoil")
        assert tank.accepts_fluid("gasoil")
        assert not tank.accepts_fluid("essence")

    def test_bac_vide_accepte_tout(self):
        assert self._tank(fluid_id=None).accepts_fluid("essence")

    def test_liste_de_compatibilite_explicite(self):
        tank = self._tank(fluid_id="gasoil", compatible_fluid_ids=("gasoil", "fuel_leger"))
        assert tank.accepts_fluid("fuel_leger")
        assert not tank.accepts_fluid("essence")

    def test_copie_par_volume(self):
        tank = self._tank()
        cible = math.pi * 100.0 * 8.0
        assert tank.with_volume(cible).current_level_m == pytest.approx(8.0)

    def test_masse_stockee(self):
        tank = self._tank()
        assert tank.mass_kg(density_kg_m3=840.0) == pytest.approx(tank.current_volume_m3 * 840.0)
