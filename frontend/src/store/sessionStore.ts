import { create } from "zustand";
import type { AnswerResult } from "@/types/api";

interface SessionState {
  mode: "voice" | "chat";
  ticker: string | null;
  timeframe: string | null;
  sessionId: string;
  priorAnswers: AnswerResult[];
  setMode: (mode: "voice" | "chat") => void;
  setTicker: (ticker: string | null) => void;
  setTimeframe: (timeframe: string | null) => void;
  addAnswer: (answer: AnswerResult) => void;
  clearSession: () => void;
}

export const useSessionStore = create<SessionState>((set) => ({
  mode: "voice",
  ticker: null,
  timeframe: null,
  sessionId: crypto.randomUUID(),
  priorAnswers: [],
  setMode: (mode) => set({ mode }),
  setTicker: (ticker) => set({ ticker }),
  setTimeframe: (timeframe) => set({ timeframe }),
  addAnswer: (answer) => set((s) => ({ priorAnswers: [...s.priorAnswers, answer] })),
  clearSession: () =>
    set({
      ticker: null,
      timeframe: null,
      sessionId: crypto.randomUUID(),
      priorAnswers: [],
    }),
}));
