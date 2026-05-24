import React, { useState, useEffect } from 'react';
import { Car, ArrowRight, ArrowLeft, Clock, Search } from 'lucide-react';
import { format } from 'date-fns';
import { supabase } from '../lib/supabase';

export const GuardDashboard = () => {
  const [occupancy, setOccupancy] = useState({ current: 0, max: 50 });
  const [dailyTotals, setDailyTotals] = useState({ entries: 0, exits: 0 });
  const [events, setEvents] = useState([]);
  const [search, setSearch] = useState('');

  // Fetch data
  useEffect(() => {
    const fetchDashboardData = async () => {
      try {
        const startOfToday = new Date();
        startOfToday.setHours(0, 0, 0, 0);
        const todayIso = startOfToday.toISOString();

        // 1. Fetch Occupancy Count (vehículos actualmente dentro en Aula Magna)
        const { count, error: countError } = await supabase
          .from('accesos')
          .select('*', { count: 'exact', head: true })
          .is('fecha_salida', null);
          
        if (!countError && count !== null) {
          setOccupancy(prev => ({ ...prev, current: count }));
        }

        // 2. Fetch Aula Magna Capacity
        const { data: zoneData, error: zoneError } = await supabase
          .from('zonas')
          .select('capacidad')
          .eq('nombre', 'Aula Magna')
          .single();
          
        if (!zoneError && zoneData) {
          setOccupancy(prev => ({ ...prev, max: zoneData.capacidad }));
        }

        // 3. Fetch Entries Today
        const { count: entriesCount, error: entriesError } = await supabase
          .from('accesos')
          .select('*', { count: 'exact', head: true })
          .gte('fecha_entrada', todayIso);

        if (!entriesError && entriesCount !== null) {
          setDailyTotals(prev => ({ ...prev, entries: entriesCount }));
        }

        // 4. Fetch Exits Today
        const { count: exitsCount, error: exitsError } = await supabase
          .from('accesos')
          .select('*', { count: 'exact', head: true })
          .gte('fecha_salida', todayIso);

        if (!exitsError && exitsCount !== null) {
          setDailyTotals(prev => ({ ...prev, exits: exitsCount }));
        }

        // 5. Fetch Latest Accesses for Timeline
        const { data, error: dataError } = await supabase
          .from('accesos')
          .select('id, vehiculo_patente, fecha_entrada, fecha_salida, confianza_ocr')
          .order('fecha_entrada', { ascending: false })
          .limit(20);

        if (!dataError && data) {
          let timeline = [];
          data.forEach(row => {
            // Entry event
            if (row.fecha_entrada) {
              timeline.push({
                id: row.id + '-in',
                plate: row.vehiculo_patente,
                type: 'in',
                timestamp: new Date(row.fecha_entrada),
                confidence: row.confianza_ocr || 0.95
              });
            }
            
            // Exit event
            if (row.fecha_salida) {
              timeline.push({
                id: row.id + '-out',
                plate: row.vehiculo_patente,
                type: 'out',
                timestamp: new Date(row.fecha_salida),
                confidence: row.confianza_ocr || 0.95
              });
            }
          });
          
          // Sort timeline descending
          timeline.sort((a, b) => b.timestamp - a.timestamp);
          setEvents(timeline.slice(0, 20));
        }
      } catch (err) {
        console.error('Error fetching guard dashboard data:', err);
      }
    };

    fetchDashboardData();

    // Subscribe to changes
    const channel = supabase.channel('guard:accesos')
      .on('postgres_changes', { event: '*', schema: 'public', table: 'accesos' }, () => {
        fetchDashboardData();
      })
      .subscribe();

    return () => {
      supabase.removeChannel(channel);
    };
  }, []);

  const filteredEvents = events.filter(e => e.plate.toLowerCase().includes(search.toLowerCase()));

  const availableSpots = occupancy.max - occupancy.current;
  const occupancyPercentage = (occupancy.current / occupancy.max) * 100;
  
  let statusColor = 'var(--status-success)';
  let statusText = 'Operando Normal';
  
  if (occupancyPercentage > 90) {
    statusColor = 'var(--status-danger)';
    statusText = 'Capacidad Llena';
  } else if (occupancyPercentage > 75) {
    statusColor = 'var(--ubb-orange)';
    statusText = 'Alta Ocupación';
  } else if (occupancyPercentage > 50) {
    statusColor = 'var(--status-warning)';
    statusText = 'Ocupación Media';
  }

  const radius = 52; // 120/2 - 8
  const circumference = 2 * Math.PI * radius;
  const strokeDashoffset = circumference - (occupancyPercentage / 100) * circumference;

  return (
    <div className="animate-fade-in">
      <div className="flex-between" style={{ marginBottom: '2rem' }}>
        <div>
          <h1 style={{ fontSize: '1.75rem', fontWeight: 700, color: 'var(--text-primary)' }}>Panel de Control (Guardia)</h1>
          <p style={{ color: 'var(--text-secondary)' }}>Monitoreo en tiempo real del Aula Magna</p>
        </div>
        <div style={{ textAlign: 'right' }}>
          <p style={{ fontSize: '0.875rem', color: 'var(--text-secondary)' }}>{format(new Date(), "dd 'de' MMMM, yyyy")}</p>
          <p style={{ fontSize: '1.25rem', fontWeight: 600 }}>{format(new Date(), "HH:mm")}</p>
        </div>
      </div>

      {/* Top Cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '1.5rem', marginBottom: '2rem' }}>
        {/* Occupancy Card */}
        <div className="card" style={{ display: 'flex', alignItems: 'center', gap: '2rem' }}>
          <div style={{ position: 'relative', width: '120px', height: '120px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <svg width="120" height="120" style={{ position: 'absolute', top: 0, left: 0, transform: 'rotate(-90deg)' }}>
              <circle 
                cx="60" cy="60" r={radius}
                fill="transparent"
                stroke="var(--border-color)"
                strokeWidth="8"
              />
              <circle 
                cx="60" cy="60" r={radius}
                fill="transparent"
                stroke={statusColor}
                strokeWidth="8"
                strokeDasharray={circumference}
                strokeDashoffset={strokeDashoffset}
                strokeLinecap="round"
                style={{ transition: 'stroke-dashoffset 1s ease-in-out, stroke 0.5s ease' }}
              />
            </svg>
            <span style={{ position: 'relative', zIndex: 10, fontSize: '2.5rem', fontWeight: 700, color: statusColor, filter: `drop-shadow(0 0 10px ${statusColor}40)` }}>{availableSpots}</span>
          </div>
          <div>
            <h3 style={{ fontSize: '1.125rem', color: 'var(--text-secondary)', marginBottom: '0.25rem' }}>Ocupación Actual</h3>
            <p style={{ fontSize: '1rem', fontWeight: 500 }}>{occupancy.current} vehículos adentro</p>
            <div style={{ display: 'inline-block', padding: '0.25rem 0.75rem', borderRadius: '9999px', backgroundColor: `${statusColor}20`, color: statusColor, fontSize: '0.875rem', fontWeight: 600, marginTop: '0.5rem' }}>
              {statusText}
            </div>
          </div>
        </div>

        {/* Quick Actions / Stats */}
        <div className="card" style={{ display: 'flex', flexDirection: 'column', justifyContent: 'center' }}>
          <h3 style={{ fontSize: '1rem', color: 'var(--text-secondary)', marginBottom: '1rem' }}>Resumen del Día</h3>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
            <div style={{ padding: '1rem', backgroundColor: 'var(--status-success-bg)', borderRadius: 'var(--radius-md)' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: '#065f46', marginBottom: '0.5rem' }}>
                <ArrowRight size={18} /> Entradas
              </div>
              <p style={{ fontSize: '1.5rem', fontWeight: 700, color: '#0f172a' }}>{dailyTotals.entries}</p>
            </div>
            <div style={{ padding: '1rem', backgroundColor: 'var(--status-warning-bg)', borderRadius: 'var(--radius-md)' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: '#92400e', marginBottom: '0.5rem' }}>
                <ArrowLeft size={18} /> Salidas
              </div>
              <p style={{ fontSize: '1.5rem', fontWeight: 700, color: '#0f172a' }}>{dailyTotals.exits}</p>
            </div>
          </div>
        </div>
      </div>

      {/* Live Feed Table */}
      <div className="card">
        <div className="flex-between" style={{ marginBottom: '1.5rem' }}>
          <h2 style={{ fontSize: '1.25rem', fontWeight: 600 }}>Registro en Vivo (Cámara IA)</h2>
          <div style={{ position: 'relative' }}>
            <Search size={18} style={{ position: 'absolute', left: '0.75rem', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-secondary)' }} />
            <input 
              type="text" 
              placeholder="Buscar patente..." 
              className="input-field" 
              style={{ paddingLeft: '2.5rem', width: '250px' }}
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </div>
        </div>

        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left' }}>
            <thead>
              <tr style={{ borderBottom: '2px solid var(--border-color)', color: 'var(--text-secondary)', fontSize: '0.875rem' }}>
                <th style={{ padding: '1rem 0.5rem' }}>Patente</th>
                <th style={{ padding: '1rem 0.5rem' }}>Movimiento</th>
                <th style={{ padding: '1rem 0.5rem' }}>Hora</th>
                <th style={{ padding: '1rem 0.5rem' }}>Confianza (IA)</th>
                <th style={{ padding: '1rem 0.5rem', textAlign: 'right' }}>Acción</th>
              </tr>
            </thead>
            <tbody>
              {filteredEvents.map((ev) => (
                <tr key={ev.id} style={{ borderBottom: '1px solid var(--border-color)' }}>
                  <td style={{ padding: '1rem 0.5rem', fontWeight: 600, fontSize: '1.125rem', letterSpacing: '1px' }}>{ev.plate}</td>
                  <td style={{ padding: '1rem 0.5rem' }}>
                    {ev.type === 'in' 
                      ? <span className="badge badge-success"><ArrowRight size={14} style={{ marginRight: '4px' }} /> Ingreso</span>
                      : <span className="badge badge-warning"><ArrowLeft size={14} style={{ marginRight: '4px' }} /> Salida</span>
                    }
                  </td>
                  <td style={{ padding: '1rem 0.5rem', color: 'var(--text-secondary)' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
                      <Clock size={14} /> {format(ev.timestamp, 'HH:mm:ss')}
                    </div>
                  </td>
                  <td style={{ padding: '1rem 0.5rem' }}>
                    <div style={{ width: '100px', height: '6px', backgroundColor: 'var(--border-color)', borderRadius: '3px', overflow: 'hidden' }}>
                      <div style={{ height: '100%', width: `${ev.confidence * 100}%`, backgroundColor: ev.confidence > 0.9 ? 'var(--status-success)' : 'var(--status-warning)' }}></div>
                    </div>
                    <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginTop: '4px', display: 'block' }}>{(ev.confidence * 100).toFixed(1)}%</span>
                  </td>
                  <td style={{ padding: '1rem 0.5rem', textAlign: 'right' }}>
                    <button className="btn btn-secondary" style={{ padding: '0.25rem 0.75rem', fontSize: '0.75rem' }}>
                      Reportar Error
                    </button>
                  </td>
                </tr>
              ))}
              {filteredEvents.length === 0 && (
                <tr>
                  <td colSpan="5" style={{ padding: '2rem', textAlign: 'center', color: 'var(--text-secondary)' }}>No se encontraron registros.</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
