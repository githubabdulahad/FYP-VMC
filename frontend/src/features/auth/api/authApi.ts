import api from "../../../lib/axios";
import type { User } from "../../../types/auth";

export const loginUser = async (username: string, password: string): Promise<User> => {
  const response = await api.post("/auth/login/", { username, password });
  return response.data.user; // backend returns { message, user }
};

export const signupUser = async (
  username: string,
  email: string,
  password: string,
  confirm_password: string
): Promise<User> => {
  const response = await api.post("/auth/register/", {
    username,
    email,
    password,
    confirm_password,
  });
  return response.data.user; // backend returns { message, user }
};

export const logoutUser = async (): Promise<void> => {
  await api.post("/auth/logout/");
};

export const getMe = async (): Promise<User> => {
  const response = await api.get("/auth/me/");
  return response.data.user; // backend returns { user: {...} }
};