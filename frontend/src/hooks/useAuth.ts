import { useEffect } from "react";
import type { Session, User } from "@supabase/supabase-js";
import { supabase } from "@/integrations/supabase/client";
import { useAuthStore } from "@/store/authStore";

/** Playwright / local UI tests only — never enable in production builds. */
const e2eAuth = import.meta.env.VITE_E2E_AUTH === "1";

export const useAuth = () => {
  const { user, session, loading, setUser, setSession, setLoading } = useAuthStore();

  useEffect(() => {
    if (e2eAuth) {
      const u = {
        id: "00000000-0000-0000-0000-000000000001",
        email: "e2e@inflect.test",
        app_metadata: {},
        user_metadata: {},
        aud: "authenticated",
        created_at: new Date().toISOString(),
      } as User;
      const s = {
        access_token: "e2e",
        refresh_token: "",
        expires_in: 999999,
        token_type: "bearer",
        user: u,
      } as Session;
      setUser(u);
      setSession(s);
      setLoading(false);
      return;
    }

    const { data: { subscription } } = supabase.auth.onAuthStateChange((_event, session) => {
      setSession(session);
      setUser(session?.user ?? null);
      setLoading(false);
    });

    supabase.auth.getSession().then(({ data: { session } }) => {
      setSession(session);
      setUser(session?.user ?? null);
      setLoading(false);
    });

    return () => subscription.unsubscribe();
  }, [setUser, setSession, setLoading]);

  const signOut = async () => {
    if (e2eAuth) {
      setUser(null);
      setSession(null);
      return;
    }
    await supabase.auth.signOut();
  };

  return { user, session, loading, signOut };
};
