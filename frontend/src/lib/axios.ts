import axios from "axios";

const api = axios.create({
  baseURL: "http://localhost:8000/api", // change this to your actual DRF backend URL
  withCredentials: true, // makes the browser send the cookies with every request
});

// endpoints that should never trigger a refresh retry
const SKIP_REFRESH = ["/auth/login/", "/auth/register/", "/auth/refresh/", "/auth/me/"];


let isRefreshing = false;

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;

    const isAuthEndpoint = SKIP_REFRESH.some((ep) =>
      originalRequest.url?.includes(ep)
    );

    // if it's an auth endpoint or already retried, just reject
    // let the calling code (ProtectedRoute, App.tsx) handle it
    if (isAuthEndpoint || originalRequest._retry || isRefreshing) {
      return Promise.reject(error);
    }

    if (error.response?.status === 401) {
      originalRequest._retry = true;
      isRefreshing = true;

      try {
        await api.post("/auth/refresh/"); // backend reads the refresh cookie, sets a new access cookie
        isRefreshing = false;
        return api(originalRequest); // retry the request that originally failed
      } catch (refreshError) {
        isRefreshing = false;
        window.location.href = "/login"; // refresh also failed, session is dead, send to login
        return Promise.reject(refreshError);
      }
    }

    return Promise.reject(error);
  }
);

export default api;