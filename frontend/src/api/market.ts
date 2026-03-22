import { apiCall } from "./client";
import type { StockQuote } from "@/types/api";

export async function getQuote(ticker: string): Promise<StockQuote> {
  return apiCall<StockQuote>(`/api/v1/market/quote?ticker=${ticker}`);
}
