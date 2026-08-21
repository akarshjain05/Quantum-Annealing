import axios from "axios";

const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

const client = axios.create({ baseURL: API_URL });

client.interceptors.response.use(
  (res) => res,
  (err) => Promise.reject(err)
);

export default client;
export { API_URL };
