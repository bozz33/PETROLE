/** Navigation interne limitée aux routes statiques de l'application. */

import {
  createContext,
  type MouseEvent,
  type PropsWithChildren,
  type ReactNode,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";

interface NavigationContextValue {
  path: string;
  navigate: (target: string, replace?: boolean) => void;
}

const NavigationContext = createContext<NavigationContextValue | null>(null);
const INTERNAL_PATH = /^\/[A-Za-z0-9/_-]*$/;

export function validatedPath(target: string): string {
  if (!INTERNAL_PATH.test(target) || target.includes("//")) {
    throw new Error("Le chemin de navigation interne est invalide.");
  }
  return target.length > 1 ? target.replace(/\/$/, "") : target;
}

export function NavigationProvider({ children }: PropsWithChildren) {
  const [path, setPath] = useState(() => validatedPath(window.location.pathname));

  useEffect(() => {
    const synchronize = () => setPath(validatedPath(window.location.pathname));
    window.addEventListener("popstate", synchronize);
    return () => window.removeEventListener("popstate", synchronize);
  }, []);

  const navigate = useCallback((target: string, replace = false) => {
    const nextPath = validatedPath(target);
    if (nextPath === window.location.pathname) {
      return;
    }
    window.history[replace ? "replaceState" : "pushState"]({}, "", nextPath);
    setPath(nextPath);
    window.scrollTo({ top: 0, behavior: "instant" });
  }, []);

  const value = useMemo(() => ({ path, navigate }), [navigate, path]);
  return <NavigationContext.Provider value={value}>{children}</NavigationContext.Provider>;
}

export function useNavigation(): NavigationContextValue {
  const context = useContext(NavigationContext);
  if (!context) {
    throw new Error("Le contexte de navigation est absent.");
  }
  return context;
}

export function InternalLink({
  to,
  className,
  children,
  label,
}: PropsWithChildren<{
  to: string;
  className?: string | ((active: boolean) => string);
  label?: string;
}>) {
  const { path, navigate } = useNavigation();
  const target = validatedPath(to);
  const active = target === "/" ? path === target : path === target || path.startsWith(target + "/");

  function follow(event: MouseEvent<HTMLAnchorElement>): void {
    if (
      event.button !== 0 ||
      event.metaKey ||
      event.ctrlKey ||
      event.shiftKey ||
      event.altKey
    ) {
      return;
    }
    event.preventDefault();
    navigate(target);
  }

  return (
    <a
      href={target}
      aria-label={label}
      aria-current={active ? "page" : undefined}
      className={typeof className === "function" ? className(active) : className}
      onClick={follow}
    >
      {children as ReactNode}
    </a>
  );
}
