import { apiCall, API_URL } from "./client";
import { supabase } from "@/integrations/supabase/client";

export interface AnalyzeResult {
  intent_type: string;
  ticker: string | null;
  metric: string | null;
  timeframe: string | null;
  confidence: number;
  answer: string;
  source: string;
  citation: string | null;
  confidence_level: "HIGH" | "MEDIUM" | "LOW";
}

export async function analyzeQuery(
  text: string,
  sessionContext: { ticker: string | null; timeframe: string | null }
): Promise<AnalyzeResult> {
  return apiCall<AnalyzeResult>("/api/v1/query/analyze", {
    method: "POST",
    body: JSON.stringify({ text, session_context: sessionContext }),
  });
}

export async function transcribeAudio(
  audioBlob: Blob
): Promise<{ transcript: string; confidence: number }> {
  const formData = new FormData();
  formData.append("audio", audioBlob, "recording.webm");

  const { data: { session } } = await supabase.auth.getSession();

  const response = await fetch(`${API_URL}/api/v1/voice/transcribe`, {
    method: "POST",
    headers: { Authorization: `Bearer ${session?.access_token}` },
    body: formData,
  });

  if (!response.ok) throw new Error(`Transcription error: ${response.status}`);
  return response.json();
}
