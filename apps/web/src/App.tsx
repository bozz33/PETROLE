import { Navigate, Route, Routes } from "react-router-dom";

import { Shell } from "./components/Shell";
import { CalculPage } from "./pages/CalculPage";
import { DecisionPage } from "./pages/DecisionPage";
import { DonneesPage } from "./pages/DonneesPage";
import { ProjetsPage } from "./pages/ProjetsPage";
import { RapportsPage } from "./pages/RapportsPage";
import { StockagePage } from "./pages/StockagePage";
import { TableauBordPage } from "./pages/TableauBordPage";

export function App() {
  return (
    <Shell>
      <Routes>
        <Route path="/" element={<TableauBordPage />} />
        <Route path="/projets" element={<ProjetsPage />} />
        <Route path="/calcul" element={<CalculPage />} />
        <Route path="/stockage" element={<StockagePage />} />
        <Route path="/decision" element={<DecisionPage />} />
        <Route path="/donnees" element={<DonneesPage />} />
        <Route path="/rapports" element={<RapportsPage />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Shell>
  );
}
