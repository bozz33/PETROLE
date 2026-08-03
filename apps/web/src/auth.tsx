/** Contrôle de l'accès à l'interface et cycle de vie de la session. */

import {
  createContext,
  type FormEvent,
  type PropsWithChildren,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";

import {
  apiRequest,
  clearSession,
  jsonBody,
  listenForSessionEnd,
  readSession,
  storeSession,
} from "./api";
import type { AuthStatus, TokenPair, UserAccount } from "./types";

interface AuthContextValue {
  user: UserAccount | null;
  localBypass: boolean;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

type AccessMode = "loading" | "local" | "login" | "bootstrap" | "authenticated" | "error";

export function AuthProvider({ children }: PropsWithChildren) {
  const [mode, setMode] = useState<AccessMode>("loading");
  const [user, setUser] = useState<UserAccount | null>(null);
  const [failure, setFailure] = useState<string | null>(null);

  async function inspectAccess(): Promise<void> {
    try {
      const status = await apiRequest<AuthStatus>("/auth/status");
      if (!status.authentication_required) {
        setMode("local");
        return;
      }
      if (!status.initialized) {
        clearSession();
        setMode("bootstrap");
        return;
      }
      if (!readSession()) {
        setMode("login");
        return;
      }
      try {
        const currentUser = await apiRequest<UserAccount>("/auth/me");
        setUser(currentUser);
        setMode("authenticated");
      } catch {
        clearSession();
        setMode("login");
      }
    } catch (error) {
      setFailure(messageOf(error));
      setMode("error");
    }
  }

  useEffect(() => {
    void inspectAccess();
    return listenForSessionEnd(() => {
      setUser(null);
      setMode("login");
    });
  }, []);

  async function acceptTokens(tokens: TokenPair): Promise<void> {
    storeSession(tokens);
    setUser(tokens.user);
    setFailure(null);
    setMode("authenticated");
  }

  async function logout(): Promise<void> {
    const current = readSession();
    try {
      if (current) {
        await apiRequest<void>("/auth/logout", {
          method: "POST",
          body: jsonBody({ refresh_token: current.refresh_token }),
        });
      }
    } finally {
      clearSession();
      setUser(null);
      setMode("login");
    }
  }

  const value = useMemo<AuthContextValue>(
    () => ({
      user,
      localBypass: mode === "local",
      logout,
    }),
    [mode, user],
  );

  if (mode === "loading") {
    return <AccessMessage title="Vérification de l'accès" detail="Connexion sécurisée en cours…" />;
  }
  if (mode === "error") {
    return (
      <AccessMessage
        title="Service indisponible"
        detail={failure ?? "L'état de la plateforme ne peut pas être chargé."}
        action={<button className="button button-primary" onClick={() => void inspectAccess()}>Réessayer</button>}
      />
    );
  }
  if (mode === "login") {
    return <LoginForm onSuccess={acceptTokens} />;
  }
  if (mode === "bootstrap") {
    return <BootstrapForm onSuccess={acceptTokens} />;
  }

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("Le contexte d'authentification est absent.");
  }
  return context;
}

function LoginForm({ onSuccess }: { onSuccess: (tokens: TokenPair) => Promise<void> }) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [failure, setFailure] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  async function submit(event: FormEvent): Promise<void> {
    event.preventDefault();
    setPending(true);
    setFailure(null);
    try {
      const tokens = await apiRequest<TokenPair>("/auth/login", {
        method: "POST",
        body: jsonBody({ email, password }),
      });
      await onSuccess(tokens);
    } catch (error) {
      setFailure(messageOf(error));
    } finally {
      setPending(false);
    }
  }

  return (
    <AccessLayout
      title="Accès à HydroPlatform"
      detail="Identifiez-vous avec le compte attribué par votre administrateur."
    >
      <form className="access-form" onSubmit={(event) => void submit(event)}>
        <label>
          Adresse électronique
          <input
            type="email"
            autoComplete="username"
            required
            value={email}
            onChange={(event) => setEmail(event.target.value)}
          />
        </label>
        <label>
          Mot de passe
          <input
            type="password"
            autoComplete="current-password"
            required
            value={password}
            onChange={(event) => setPassword(event.target.value)}
          />
        </label>
        {failure ? <p className="access-error" role="alert">{failure}</p> : null}
        <button className="button button-primary" disabled={pending}>
          {pending ? "Connexion…" : "Se connecter"}
        </button>
      </form>
    </AccessLayout>
  );
}

function BootstrapForm({ onSuccess }: { onSuccess: (tokens: TokenPair) => Promise<void> }) {
  const [failure, setFailure] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  async function submit(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    setPending(true);
    setFailure(null);
    const form = new FormData(event.currentTarget);
    try {
      const tokens = await apiRequest<TokenPair>("/auth/bootstrap", {
        method: "POST",
        body: jsonBody({
          email: form.get("email"),
          full_name: form.get("full_name"),
          password: form.get("password"),
          organization_name: form.get("organization_name"),
          organization_slug: form.get("organization_slug"),
        }),
      });
      await onSuccess(tokens);
    } catch (error) {
      setFailure(messageOf(error));
    } finally {
      setPending(false);
    }
  }

  return (
    <AccessLayout
      title="Initialiser la plateforme"
      detail="Créez l'organisation et son premier administrateur. Cette étape n'est disponible qu'une fois."
    >
      <form className="access-form" onSubmit={(event) => void submit(event)}>
        <div className="form-grid">
          <label>
            Organisation
            <input name="organization_name" required minLength={2} />
          </label>
          <label>
            Identifiant de l'organisation
            <input
              name="organization_slug"
              required
              minLength={2}
              pattern="[a-z0-9]+(?:-[a-z0-9]+)*"
              placeholder="transport-nord"
            />
          </label>
          <label>
            Nom complet
            <input name="full_name" autoComplete="name" required minLength={2} />
          </label>
          <label>
            Adresse électronique
            <input name="email" type="email" autoComplete="username" required />
          </label>
        </div>
        <label>
          Mot de passe administrateur
          <input
            name="password"
            type="password"
            autoComplete="new-password"
            required
            minLength={12}
          />
          <small>12 caractères minimum. Utilisez une phrase secrète unique.</small>
        </label>
        {failure ? <p className="access-error" role="alert">{failure}</p> : null}
        <button className="button button-primary" disabled={pending}>
          {pending ? "Initialisation…" : "Créer l'accès administrateur"}
        </button>
      </form>
    </AccessLayout>
  );
}

function AccessLayout({
  title,
  detail,
  children,
}: PropsWithChildren<{ title: string; detail: string }>) {
  return (
    <main className="access-page">
      <section className="access-card">
        <div className="access-brand">
          <span className="brand-symbol" aria-hidden="true">HP</span>
          <span>
            <strong>HydroPlatform</strong>
            <small>Ingénierie liquide</small>
          </span>
        </div>
        <p className="eyebrow">Plateforme Hydrocarbures</p>
        <h1>{title}</h1>
        <p className="access-detail">{detail}</p>
        {children}
      </section>
    </main>
  );
}

function AccessMessage({
  title,
  detail,
  action,
}: {
  title: string;
  detail: string;
  action?: React.ReactNode;
}) {
  return (
    <AccessLayout title={title} detail={detail}>
      {action ? <div className="button-row">{action}</div> : <div className="access-loader" />}
    </AccessLayout>
  );
}

function messageOf(error: unknown): string {
  return error instanceof Error ? error.message : "Une erreur inattendue est survenue.";
}
