/** Adaptateur de navigation conservant le contrat interne sur TanStack Router. */

import { useNavigate, useRouterState } from "@tanstack/react-router";
import {
  type MouseEvent,
  type PropsWithChildren,
  type ReactNode,
  useCallback,
} from "react";

interface NavigationContextValue {
  path: string;
  navigate: (target: string, replace?: boolean) => void;
}

const INTERNAL_PATH = /^\/[A-Za-z0-9/_-]*$/;

export function validatedPath(target: string): string {
  if (!INTERNAL_PATH.test(target) || target.includes("//")) {
    throw new Error("Le chemin de navigation interne est invalide.");
  }
  return target.length > 1 ? target.replace(/\/$/, "") : target;
}

/**
 * Composant de compatibilité temporaire. Le fournisseur réel est désormais
 * RouterProvider dans main.tsx.
 */
export function NavigationProvider({ children }: PropsWithChildren) {
  return <>{children}</>;
}

export function useNavigation(): NavigationContextValue {
  const path = useRouterState({ select: (state) => state.location.pathname });
  const tanstackNavigate = useNavigate();

  const navigate = useCallback(
    (target: string, replace = false) => {
      const nextPath = validatedPath(target);
      void tanstackNavigate({ to: nextPath as never, replace });
    },
    [tanstackNavigate],
  );

  return { path: validatedPath(path), navigate };
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
