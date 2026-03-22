import { supabase } from "@/integrations/supabase/client";
import type { Position, Trade } from "@/types/api";

export async function getPositions(): Promise<Position[]> {
  const { data, error } = await supabase
    .from("positions")
    .select("*")
    .order("created_at", { ascending: false });

  if (error) throw error;
  return data as unknown as Position[];
}

export async function getTrades(limit = 50): Promise<Trade[]> {
  const { data, error } = await supabase
    .from("trades")
    .select("*")
    .order("created_at", { ascending: false })
    .limit(limit);

  if (error) throw error;
  return data as unknown as Trade[];
}
