import { Routes, Route } from 'react-router-dom';
import { Sidebar } from './components/Sidebar';
import { Header } from './components/Header';
import { Dashboard } from './pages/Dashboard';
import { DataSources } from './pages/DataSources';
import { MLPipeline } from './pages/MLPipeline';
import { CreditDecisioning } from './pages/CreditDecisioning';
import { KnowledgeBase } from './pages/KnowledgeBase';
import { Monitoring } from './pages/Monitoring';

export default function App() {
  return (
    <div className="app-layout">
      <Sidebar />
      <div className="app-main">
        <Header />
        <main className="app-content">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/data" element={<DataSources />} />
            <Route path="/ml" element={<MLPipeline />} />
            <Route path="/decisioning" element={<CreditDecisioning />} />
            <Route path="/knowledge" element={<KnowledgeBase />} />
            <Route path="/monitoring" element={<Monitoring />} />
          </Routes>
        </main>
      </div>
    </div>
  );
}
