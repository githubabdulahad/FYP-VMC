import api from "../../../lib/axios";
import type { CodingResult, UploadStatus } from "../../../types/document";

// list of all coding results for logged-in user
export const getCodingResults = async (): Promise<CodingResult[]> => {
  const response = await api.get("/coding/");
  return response.data.results ?? response.data;
};

// poll a single upload record while it's still processing
export const getUploadStatus = async (id: number): Promise<UploadStatus> => {
  const response = await api.get(`/ingestion/upload/${id}/`);
  return response.data;
};