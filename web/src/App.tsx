import { Routes, Route } from "react-router-dom";
import Layout from "./components/Layout";
import Dashboard from "./pages/Dashboard";
import Signals from "./pages/Signals";
import Leads from "./pages/Leads";
import LeadDetail from "./pages/LeadDetail";
import Offers from "./pages/Offers";
import Settings from "./pages/Settings";

export default function App() {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/signals" element={<Signals />} />
        <Route path="/leads" element={<Leads />} />
        <Route path="/leads/:id" element={<LeadDetail />} />
        <Route path="/offers" element={<Offers />} />
        <Route path="/settings" element={<Settings />} />
      </Routes>
    </Layout>
  );
}