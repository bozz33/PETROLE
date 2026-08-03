import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

import { App } from "./App";
import { AuthProvider } from "./auth";
import { NavigationProvider } from "./routing";
import { ThemeProvider } from "./theme";
import "./styles.css";
import "./petrole-theme.css";
import "./shadcn-shell.css";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 15_000,
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
});

const container = document.getElementById("root");
if (!container) {
  throw new Error("Le conteneur racine de l'interface est introuvable.");
}

createRoot(container).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <ThemeProvider>
        <NavigationProvider>
          <AuthProvider>
            <App />
          </AuthProvider>
        </NavigationProvider>
      </ThemeProvider>
    </QueryClientProvider>
  </StrictMode>,
);
