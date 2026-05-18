import React from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, LineChart, Line } from 'recharts';
import { Download, AlertTriangle, Filter } from 'lucide-react';

const mockDailyData = [
  { time: '08:00', ocupacion: 45 },
  { time: '09:00', ocupacion: 110 },
  { time: '10:00', ocupacion: 145 },
  { time: '11:00', ocupacion: 148 },
  { time: '12:00', ocupacion: 130 },
  { time: '13:00', ocupacion: 115 },
  { time: '14:00', ocupacion: 140 },
  { time: '15:00', ocupacion: 135 },
  { time: '16:00', ocupacion: 90 },
  { time: '17:00', ocupacion: 60 },
  { time: '18:00', ocupacion: 20 },
];

const mockIncidents = [
  { id: 1, plate: 'CRJC39', issue: 'Mala lectura OCR', date: '2026-05-17', status: 'Pendiente' },
  { id: 2, plate: 'AB1234', issue: 'Vehículo mal estacionado', date: '2026-05-16', status: 'Resuelto' },
];

export const ManagerDashboard = () => {
  return (
    <div className="animate-fade-in">
      <div className="flex-between" style={{ marginBottom: '2rem' }}>
        <div>
          <h1 style={{ fontSize: '1.75rem', fontWeight: 700, color: 'var(--text-primary)' }}>Panel Ejecutivo (Encargado)</h1>
          <p style={{ color: 'var(--text-secondary)' }}>Estadísticas, KPIs y Gestión de Incidencias</p>
        </div>
        <div style={{ display: 'flex', gap: '1rem' }}>
          <button className="btn btn-secondary">
            <Filter size={18} /> Filtros (Hoy)
          </button>
          <button className="btn btn-primary">
            <Download size={18} /> Exportar Reporte
          </button>
        </div>
      </div>

      {/* KPI Cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '1.5rem', marginBottom: '2rem' }}>
        <div className="card">
          <h3 style={{ fontSize: '0.875rem', color: 'var(--text-secondary)', marginBottom: '0.5rem' }}>Ocupación Máxima (Día)</h3>
          <p style={{ fontSize: '2rem', fontWeight: 700, color: 'var(--ubb-blue)' }}>98.6%</p>
          <p style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>A las 11:15 hrs</p>
        </div>
        <div className="card">
          <h3 style={{ fontSize: '0.875rem', color: 'var(--text-secondary)', marginBottom: '0.5rem' }}>Total Vehículos Únicos</h3>
          <p style={{ fontSize: '2rem', fontWeight: 700, color: 'var(--ubb-orange)' }}>342</p>
          <p style={{ fontSize: '0.75rem', color: 'var(--status-success)' }}>+12% vs ayer</p>
        </div>
        <div className="card">
          <h3 style={{ fontSize: '0.875rem', color: 'var(--text-secondary)', marginBottom: '0.5rem' }}>Tiempo Promedio Estadia</h3>
          <p style={{ fontSize: '2rem', fontWeight: 700, color: 'var(--text-primary)' }}>3.2 hrs</p>
          <p style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>En vehículos registrados</p>
        </div>
        <div className="card" style={{ borderLeft: '4px solid var(--status-danger)' }}>
          <h3 style={{ fontSize: '0.875rem', color: 'var(--text-secondary)', marginBottom: '0.5rem' }}>Incidencias Activas</h3>
          <p style={{ fontSize: '2rem', fontWeight: 700, color: 'var(--status-danger)' }}>3</p>
          <p style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>Requieren atención</p>
        </div>
      </div>

      {/* Charts */}
      <div className="card" style={{ marginBottom: '2rem' }}>
        <h2 style={{ fontSize: '1.25rem', fontWeight: 600, marginBottom: '1.5rem' }}>Curva de Ocupación Diaria</h2>
        <div style={{ height: '300px', width: '100%' }}>
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={mockDailyData} margin={{ top: 5, right: 20, bottom: 5, left: 0 }}>
              <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="var(--border-color)" />
              <XAxis dataKey="time" stroke="var(--text-secondary)" fontSize={12} />
              <YAxis stroke="var(--text-secondary)" fontSize={12} domain={[0, 150]} />
              <Tooltip 
                contentStyle={{ backgroundColor: 'var(--bg-secondary)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-color)' }}
              />
              <Line type="monotone" dataKey="ocupacion" stroke="var(--ubb-blue)" strokeWidth={3} dot={{ r: 4, strokeWidth: 2 }} activeDot={{ r: 8 }} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Incidents Table */}
      <div className="card">
        <div className="flex-between" style={{ marginBottom: '1.5rem' }}>
          <h2 style={{ fontSize: '1.25rem', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <AlertTriangle size={20} color="var(--status-warning)" /> Gestión de Incidencias
          </h2>
          <button className="btn btn-secondary">Nueva Incidencia</button>
        </div>

        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left' }}>
            <thead>
              <tr style={{ borderBottom: '2px solid var(--border-color)', color: 'var(--text-secondary)', fontSize: '0.875rem' }}>
                <th style={{ padding: '1rem 0.5rem' }}>ID</th>
                <th style={{ padding: '1rem 0.5rem' }}>Patente/Evento</th>
                <th style={{ padding: '1rem 0.5rem' }}>Descripción</th>
                <th style={{ padding: '1rem 0.5rem' }}>Fecha</th>
                <th style={{ padding: '1rem 0.5rem' }}>Estado</th>
                <th style={{ padding: '1rem 0.5rem', textAlign: 'right' }}>Acciones</th>
              </tr>
            </thead>
            <tbody>
              {mockIncidents.map((inc) => (
                <tr key={inc.id} style={{ borderBottom: '1px solid var(--border-color)' }}>
                  <td style={{ padding: '1rem 0.5rem', color: 'var(--text-secondary)' }}>#{inc.id}</td>
                  <td style={{ padding: '1rem 0.5rem', fontWeight: 600 }}>{inc.plate}</td>
                  <td style={{ padding: '1rem 0.5rem' }}>{inc.issue}</td>
                  <td style={{ padding: '1rem 0.5rem', color: 'var(--text-secondary)' }}>{inc.date}</td>
                  <td style={{ padding: '1rem 0.5rem' }}>
                    <span className={`badge ${inc.status === 'Resuelto' ? 'badge-success' : 'badge-warning'}`}>
                      {inc.status}
                    </span>
                  </td>
                  <td style={{ padding: '1rem 0.5rem', textAlign: 'right' }}>
                    <button className="btn btn-secondary" style={{ padding: '0.25rem 0.75rem', fontSize: '0.75rem' }}>
                      Revisar
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
