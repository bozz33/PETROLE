"""Tests du paquet canonique et de son rejeu sans dépendance au catalogue."""

from __future__ import annotations

from copy import deepcopy

import pytest
from tests.factories import (
    bac,
    brut_leger,
    entree_canonique,
    pipeline,
    profil_plat,
    segment,
    station_serie,
)

from hydro_domain import (
    CanonicalInput,
    EquipmentStatus,
    Fitting,
    InjectionPoint,
    InterpolationKind,
    Pipeline,
    PumpCurve,
    PumpInstance,
    PumpModel,
    PumpOverride,
    Scenario,
    SegmentOverride,
    StationOverride,
    build_series_station,
    canonical_input_from_dict,
)
from hydro_shared.errors import InvalidInputError
from hydro_shared.hashing import canonical_json


def _entree_avec_modele(model: PumpModel) -> CanonicalInput:
    station = build_series_station(
        id="S1",
        name="Station 1",
        chainage_m=0.0,
        elevation_m=100.0,
        pumps=(PumpInstance(id="P1", model=model),),
    )
    return entree_canonique(conduite=pipeline(stations=(station,)))


class TestCatalogueCanonique:
    def test_les_courbes_de_pompe_sont_figees_et_dedoublonnees(self):
        entree = entree_canonique(conduite=pipeline(stations=(station_serie(),)))

        models = entree.payload()["equipment"]["pump_models"]

        assert len(models) == 1
        assert models[0]["id"] == "NM-8"
        assert models[0]["curve"]["flows_m3_s"]
        assert models[0]["curve"]["heads_m"]
        assert models[0]["curve"]["interpolation"] == "pchip"

    def test_une_courbe_differente_change_l_empreinte(self):
        model_a = PumpModel(
            id="M1",
            name="Modèle 1",
            curve=PumpCurve([0.0, 0.2, 0.4], [120.0, 100.0, 60.0]),
        )
        model_b = PumpModel(
            id="M1",
            name="Modèle 1",
            curve=PumpCurve([0.0, 0.2, 0.4], [125.0, 105.0, 65.0]),
        )

        assert _entree_avec_modele(model_a).fingerprint != _entree_avec_modele(model_b).fingerprint

    def test_un_manifeste_normatif_different_change_l_empreinte(self):
        source = entree_canonique()
        first = CanonicalInput(
            pipeline=source.pipeline,
            fluid=source.fluid,
            scenario=source.scenario,
            engine=source.engine,
            rule_set_ids=("11111111-1111-1111-1111-111111111111",),
            rule_manifest=({"content_hash": "sha256:a", "rules": []},),
        )
        second = CanonicalInput(
            pipeline=source.pipeline,
            fluid=source.fluid,
            scenario=source.scenario,
            engine=source.engine,
            rule_set_ids=("11111111-1111-1111-1111-111111111111",),
            rule_manifest=({"content_hash": "sha256:b", "rules": []},),
        )

        assert first.fingerprint != second.fingerprint
        restored = canonical_input_from_dict(first.as_dict())
        assert restored.rule_manifest == first.rule_manifest

    def test_la_methode_d_interpolation_change_l_empreinte(self):
        linear = PumpModel(
            id="M1",
            name="Modèle 1",
            curve=PumpCurve(
                [0.0, 0.2, 0.4],
                [120.0, 100.0, 60.0],
                interpolation=InterpolationKind.LINEAR,
            ),
        )
        pchip = PumpModel(
            id="M1",
            name="Modèle 1",
            curve=PumpCurve(
                [0.0, 0.2, 0.4],
                [120.0, 100.0, 60.0],
                interpolation=InterpolationKind.PCHIP,
            ),
        )

        assert _entree_avec_modele(linear).fingerprint != _entree_avec_modele(pchip).fingerprint

    def test_un_identifiant_ambigu_est_rejete(self):
        model_a = PumpModel(
            id="M1",
            name="Modèle 1",
            curve=PumpCurve([0.0, 0.2], [100.0, 60.0]),
        )
        model_b = PumpModel(
            id="M1",
            name="Modèle 1",
            curve=PumpCurve([0.0, 0.2], [110.0, 70.0]),
        )
        station = build_series_station(
            id="S1",
            name="Station 1",
            chainage_m=0.0,
            elevation_m=100.0,
            pumps=(
                PumpInstance(id="P1", model=model_a),
                PumpInstance(id="P2", model=model_b),
            ),
        )
        entree = entree_canonique(conduite=pipeline(stations=(station,)))

        with pytest.raises(InvalidInputError, match="plusieurs courbes"):
            entree.payload()


class TestReconstructionCanonique:
    def test_aller_retour_complet_conserve_le_payload_et_l_empreinte(self):
        conduit = Pipeline(
            id="PL-RICHE",
            name="Pipeline riche",
            segments=(
                segment(
                    identifiant="T1",
                    longueur_m=50_000.0,
                    fittings=(
                        Fitting(
                            id="V1",
                            kind="vanne",
                            k_coefficient=0.8,
                            quantity=2,
                            opening_ratio=0.9,
                        ),
                    ),
                ),
            ),
            profile=profil_plat(),
            stations=(station_serie(),),
            injections=(
                InjectionPoint(
                    id="INJ1",
                    chainage_m=25_000.0,
                    flow_m3_s=0.01,
                ),
            ),
            origin_tank=bac("B-AMONT", fluid_id="brut-leger"),
            destination_tank=bac(
                "B-AVAL",
                fluid_id=None,
                compatible_fluid_ids=("brut-leger",),
            ),
        )
        cas = Scenario(
            id="SC-RICHE",
            name="Scénario riche",
            temperature_k=303.15,
            imposed_flow_m3_s=0.2,
            inlet_pressure_pa=5.0e6,
            pump_overrides=(PumpOverride(pump_id="S1-P1", speed_ratio=0.9),),
            station_overrides=(StationOverride(station_id="S1", status=EquipmentStatus.AVAILABLE),),
            segment_overrides=(SegmentOverride(segment_id="T1", additional_k=1.2),),
            description="Cas de rejeu complet.",
        )
        source = entree_canonique(conduite=conduit, fluide=brut_leger(), cas=cas)

        restored = canonical_input_from_dict(source.as_dict())

        assert canonical_json(restored.payload()) == canonical_json(source.payload())
        assert restored.fingerprint == source.fingerprint
        assert restored.as_dict()["provenance"] == source.as_dict()["provenance"]

    def test_un_modele_reference_mais_absent_est_rejete(self):
        source = entree_canonique(conduite=pipeline(stations=(station_serie(),))).payload()
        broken = deepcopy(source)
        broken["equipment"]["pump_models"] = []

        with pytest.raises(InvalidInputError, match="modèle absent"):
            canonical_input_from_dict(broken)

    def test_les_identifiants_du_manifest_sont_controles(self):
        source = entree_canonique().payload()
        broken = deepcopy(source)
        broken["manifest"]["fluid_id"] = "produit-inconnu"

        with pytest.raises(InvalidInputError, match="ne correspond pas"):
            canonical_input_from_dict(broken)
