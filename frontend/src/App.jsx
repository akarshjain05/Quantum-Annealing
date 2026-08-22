import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import Layout from "./components/Layout";
import Dashboard from "./pages/Dashboard";
import Corridors from "./pages/Corridors";
import Optimizer from "./pages/Optimizer";
import QuboInspector from "./pages/QuboInspector";
import StressTests from "./pages/StressTests";
import Agent from "./pages/Agent";
import Audit from "./pages/Audit";

export default function App() {
  return (
    <BrowserRouter>
      <Layout>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/corridors" element={<Corridors />} />
          <Route path="/optimizer" element={<Optimizer />} />
          <Route path="/stress-tests" element={<StressTests />} />
          <Route path="/agent" element={<Agent />} />
          <Route path="/audit" element={<Audit />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </Layout>
    </BrowserRouter>
  );
}
