import { Shell } from "./components/Shell";
import { AdministrationPage } from "./pages/AdministrationPage";
import { CalculPage } from "./pages/CalculPage";
import { DecisionPage } from "./pages/DecisionPage";
import { DonneesPage } from "./pages/DonneesPage";
import { ProjetsPage } from "./pages/ProjetsPage";
import { RapportsPage } from "./pages/RapportsPage";
import { StockagePage } from "./pages/StockagePage";
import { TableauBordPage } from "./pages/TableauBordPage";
import { useNavigation } from "./routing";

const PAGES: Record<string, () => JSX.Element> = {
  "/": TableauBordPage,
  "/projets": ProjetsPage,
  "/calcul": CalculPage,
  "/stockage": StockagePage,
  "/decision": DecisionPage,
  "/donnees": DonneesPage,
  "/rapports": RapportsPage,
  "/administration": AdministrationPage,
};

export function App() {
  const { path } = useNavigation();
  const Page = PAGES[path] ?? TableauBordPage;

  return (
    <Shell>
      <Page />
    </Shell>
  );
}
