import axios from "../../../lib/axios";
import type { UploadPayload, UploadRecord } from "../../../types/document";

// --- 1. Upload file to Cloudinary ---
export async function uploadToCloudinary(file: File): Promise<string> {
  const cloudName = import.meta.env.VITE_CLOUDINARY_CLOUD_NAME;
  const uploadPreset = import.meta.env.VITE_CLOUDINARY_UPLOAD_PRESET;

  const formData = new FormData();
  formData.append("file", file);
  formData.append("upload_preset", uploadPreset);

  // We use native fetch here, NOT our axios instance
  // because this request goes to Cloudinary, not our Django backend
  const response = await fetch(
    `https://api.cloudinary.com/v1_1/${cloudName}/auto/upload`,
    { method: "POST", body: formData }
  );

  if (!response.ok) {
    throw new Error("Cloudinary upload failed");
  }

  const data = await response.json();
  return data.secure_url; // this is the URL we send to Django
}

// --- 2. Submit upload record to Django ---
export async function createUploadRecord(
  payload: UploadPayload
): Promise<UploadRecord> {
  const response = await axios.post("/ingestion/upload/", payload);
  return response.data;
}

// --- 3. Poll upload status ---
export async function getUploadStatus(id: number): Promise<UploadRecord> {
  const response = await axios.get(`/ingestion/upload/${id}/`);
  return response.data;
}