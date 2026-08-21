import axios from "axios";

const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

const client = axios.create({ baseURL: API_URL });

<<<<<<< HEAD
client.interceptors.request.use((config) => {
  const token = localStorage.getItem("nostroq_token");
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

client.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response && err.response.status === 401) {
      localStorage.removeItem("nostroq_token");
      localStorage.removeItem("nostroq_user");
      if (window.location.pathname !== "/login") {
        window.location.href = "/login";
      }
    }
    return Promise.reject(err);
  }
=======
client.interceptors.response.use(
  (res) => res,
  (err) => Promise.reject(err)
>>>>>>> origin/main
);

export default client;
export { API_URL };
