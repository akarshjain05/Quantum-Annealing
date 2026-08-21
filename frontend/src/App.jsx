import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
<<<<<<< HEAD
import { AuthProvider, useAuth } from "./AuthContext";
import Layout from "./components/Layout";
import Login from "./pages/Login";
=======
import Layout from "./components/Layout";
>>>>>>> origin/main
import Dashboard from "./pages/Dashboard";
import Corridors from "./pages/Corridors";
import Optimizer from "./pages/Optimizer";
import QuboInspector from "./pages/QuboInspector";
import Scenarios from "./pages/Scenarios";
import StressTests from "./pages/StressTests";
import Agent from "./pages/Agent";
import Audit from "./pages/Audit";

<<<<<<< HEAD
function Protected({ children }) {
  const { isAuthenticated } = useAuth();
  if (!isAuthenticated) return <Navigate to="/login" replace />;
  return <Layout>{children}</Layout>;
}

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route path="/" element={<Protected><Dashboard /></Protected>} />
          <Route path="/corridors" element={<Protected><Corridors /></Protected>} />
          <Route path="/optimizer" element={<Protected><Optimizer /></Protected>} />
          <Route path="/qubo" element={<Protected><QuboInspector /></Protected>} />
          <Route path="/scenarios" element={<Protected><Scenarios /></Protected>} />
          <Route path="/stress-tests" element={<Protected><StressTests /></Protected>} />
          <Route path="/agent" element={<Protected><Agent /></Protected>} />
          <Route path="/audit" element={<Protected><Audit /></Protected>} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
=======
export default function App() {
  return (
    <BrowserRouter>
      <Layout>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/corridors" element={<Corridors />} />
          <Route path="/optimizer" element={<Optimizer />} />
          <Route path="/qubo" element={<QuboInspector />} />
          <Route path="/scenarios" element={<Scenarios />} />
          <Route path="/stress-tests" element={<StressTests />} />
          <Route path="/agent" element={<Agent />} />
          <Route path="/audit" element={<Audit />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </Layout>
    </BrowserRouter>
>>>>>>> origin/main
  );
}
