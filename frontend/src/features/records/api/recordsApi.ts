import axios from "../../../lib/axios";
import type { CodingResult } from "../../../types/document";

// Fetch all coding results (same as review)
export async function getCodingResults(): Promise<CodingResult[]> {
  const response = await axios.get("/coding/");
  return response.data;
}