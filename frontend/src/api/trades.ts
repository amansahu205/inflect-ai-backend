import { apiCall } from "./client";

export interface TradeResult {
  fill_price: number;
  total_value: number;
  status: string;
}

export async function executeTrade(order: {
  ticker: string;
  side: "buy" | "sell";
  quantity: number;
  order_type: "market";
}): Promise<TradeResult> {
  return apiCall<TradeResult>("/api/v1/trades/execute", {
    method: "POST",
    body: JSON.stringify(order),
  });
}
