import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import Layout from "./components/Layout";
import Dashboard from "./pages/Dashboard";
import Corridors from "./pages/Corridors";
import Optimizer from "./pages/Optimizer";
import QuboInspector from "./pages/QuboInspector";
import Scenarios from "./pages/Scenarios";
import StressTests from "./pages/StressTests";
import Agent from "./pages/Agent";
import Audit from "./pages/Audit";
import Login from "./pages/Login";
import Liquidity from "./pages/Liquidity";
import NostroAccounts from "./pages/NostroAccounts";
import Forecast from "./pages/Forecast";
import Regulatory from "./pages/Regulatory";
import OptimizationRuns from "./pages/OptimizationRuns";
import Settings from "./pages/Settings";


export default function App() {
  return (
    <BrowserRouter>
      
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route path="/*" element={
            <Layout>
              <Routes>
                <Route path="/" element={<Dashboard />} />
                <Route path="/liquidity" element={<Liquidity />} />
                <Route path="/corridors" element={<Corridors />} />
                <Route path="/nostro" element={<NostroAccounts />} />
                <Route path="/forecast" element={<Forecast />} />
                <Route path="/optimizer" element={<Optimizer />} />
                <Route path="/qubo" element={<QuboInspector />} />
                <Route path="/scenarios" element={<Scenarios />} />
                <Route path="/stress" element={<StressTests />} />
                <Route path="/agent" element={<Agent />} />
                <Route path="/regulatory" element={<Regulatory />} />
                <Route path="/optimization-runs" element={<OptimizationRuns />} />
                <Route path="/audit" element={<Audit />} />
                <Route path="/settings" element={<Settings />} />
                <Route path="*" element={<Navigate to="/" replace />} />
              </Routes>
            </Layout>
          } />
        </Routes>

    </BrowserRouter>
  );
}
