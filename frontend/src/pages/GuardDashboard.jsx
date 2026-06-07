import React, { useState, useEffect } from 'react';
import { Car, ArrowRight, ArrowLeft, Clock, Search, X } from 'lucide-react';
import { format } from 'date-fns';
import { supabase } from '../lib/supabase';

const modalOverlayStyle = {
  position: 'fixed',
  top: 0,
  left: 0,
  right: 0,
  bottom: 0,
  backgroundColor: 'rgba(15, 23, 42, 0.6)',
  backdropFilter: 'blur(8px)',
  display: 'flex',
  justifyContent: 'center',
  alignItems: 'center',
  zIndex: 1000,
};

const modalContentStyle = {
  width: '100%',
  maxWidth: '500px',
  backgroundColor: 'var(--bg-secondary)',
  borderRadius: 'var(--radius-lg)',
  border: '1px solid var(--border-color)',
  boxShadow: 'var(--shadow-lg)',
  padding: '2rem',
  position: 'relative',
};

export const GuardDashboard = () => {
  const [occupancy, setOccupancy] = useState({ current: 0, max: 50 });
  const [dailyTotals, setDailyTotals] = useState({ entries: 0, exits: 0 });
  const [currentTime, setCurrentTime] = useState(new Date());
  const [events, setEvents] = useState([]);
  const [search, setSearch] = useState('');
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);

  // Reset page to 1 when search or pageSize changes
  useEffect(() => {
    setCurrentPage(1);
  }, [search, pageSize]);

  // Modal and incident states
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [selectedEvent, setSelectedEvent] = useState(null);
  const [incidentType, setIncidentType] = useState('Vehículo mal estacionado');
  const [description, setDescription] = useState('');
  const [submitting, setSubmitting] = useState(false);

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
          .select('id, vehiculo_patente, fecha_entrada, fecha_salida, confianza_ocr, zona_id')
          .order('fecha_entrada', { ascending: false })
          .limit(500);

        if (!dataError && data) {
          let timeline = [];
          data.forEach(row => {
            // Entry event
            if (row.fecha_entrada) {
              timeline.push({
                id: row.id + '-in',
                accessId: row.id,
                zoneId: row.zona_id,
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
                accessId: row.id,
                zoneId: row.zona_id,
                plate: row.vehiculo_patente,
                type: 'out',
                timestamp: new Date(row.fecha_salida),
                confidence: row.confianza_ocr || 0.95
              });
            }
          });
          
          // Sort timeline descending
          timeline.sort((a, b) => b.timestamp - a.timestamp);
          setEvents(timeline);
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

  useEffect(() => {
    const interval = setInterval(() => {
      setCurrentTime(new Date());
    }, 1000);
    return () => clearInterval(interval);
  }, []);

  const filteredEvents = events.filter(e => e.plate.toLowerCase().includes(search.toLowerCase()));
  const totalItems = filteredEvents.length;
  const totalPages = Math.ceil(totalItems / pageSize) || 1;
  const paginatedEvents = filteredEvents.slice((currentPage - 1) * pageSize, currentPage * pageSize);

  const handleOpenModal = (ev) => {
    setSelectedEvent(ev);
    setIncidentType('Vehículo mal estacionado');
    setDescription('');
    setIsModalOpen(true);
  };

  const handleReportIncident = async (e) => {
    e.preventDefault();
    if (!selectedEvent || !description.trim()) return;

    setSubmitting(true);
    try {
      const { data: { user } } = await supabase.auth.getUser();
      
      const newInc = {
        acceso_id: selectedEvent.accessId,
        vehiculo_patente: selectedEvent.plate,
        tipo: incidentType,
        descripcion: description.trim(),
        zona_id: selectedEvent.zoneId || null,
        usuario_id: user ? user.id : null,
        estado: 'abierta',
      };

      const { error } = await supabase
        .from('incidencias')
        .insert([newInc]);

      if (error) throw error;

      alert('Incidencia registrada exitosamente.');
      setIsModalOpen(false);
      setSelectedEvent(null);
    } catch (err) {
      console.error('Error reporting incident:', err);
      alert('Error al registrar incidencia: ' + err.message);
    } finally {
      setSubmitting(false);
    }
  };

  const availableSpots = Math.max(0, occupancy.max - occupancy.current);
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
  const clampedPercentage = Math.min(100, Math.max(0, occupancyPercentage));
  const strokeDashoffset = circumference - (clampedPercentage / 100) * circumference;

  return (
    <div className="animate-fade-in">
      <div className="flex-between" style={{ marginBottom: '2rem' }}>
        <div>
          <h1 style={{ fontSize: '1.75rem', fontWeight: 700, color: 'var(--text-primary)' }}>Panel de Control (Guardia)</h1>
          <p style={{ color: 'var(--text-secondary)' }}>Monitoreo en tiempo real del Aula Magna</p>
        </div>
        <div style={{ textAlign: 'right' }}>
          <p style={{ fontSize: '0.875rem', color: 'var(--text-secondary)' }}>{format(currentTime, "dd 'de' MMMM, yyyy")}</p>
          <p style={{ fontSize: '1.25rem', fontWeight: 600 }}>{format(currentTime, "HH:mm:ss")}</p>
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
        <div className="flex-between" style={{ marginBottom: '1.5rem', flexWrap: 'wrap', gap: '1rem' }}>
          <h2 style={{ fontSize: '1.25rem', fontWeight: 600 }}>Registro en Vivo (Cámara)</h2>
          <div style={{ display: 'flex', gap: '1rem', alignItems: 'center', flexWrap: 'wrap' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <span style={{ fontSize: '0.875rem', color: 'var(--text-secondary)' }}>Mostrar:</span>
              <select 
                value={pageSize} 
                onChange={(e) => setPageSize(Number(e.target.value))}
                className="input-field"
                style={{ width: '80px', padding: '0.25rem 0.5rem', height: '38px' }}
              >
                <option value={20}>20</option>
                <option value={30}>30</option>
                <option value={50}>50</option>
              </select>
            </div>
            <div style={{ position: 'relative' }}>
              <Search size={18} style={{ position: 'absolute', left: '0.75rem', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-secondary)' }} />
              <input 
                type="text" 
                placeholder="Buscar patente..." 
                className="input-field" 
                style={{ paddingLeft: '2.5rem', width: '220px', height: '38px' }}
                value={search}
                onChange={(e) => setSearch(e.target.value)}
              />
            </div>
          </div>
        </div>

        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left' }}>
            <thead>
              <tr style={{ borderBottom: '2px solid var(--border-color)', color: 'var(--text-secondary)', fontSize: '0.875rem' }}>
                <th style={{ padding: '1rem 0.5rem', textAlign: 'center' }}>Patente</th>
                <th style={{ padding: '1rem 0.5rem', textAlign: 'center' }}>Movimiento</th>
                <th style={{ padding: '1rem 0.5rem', textAlign: 'center' }}>Fecha/Hora</th>
                <th style={{ padding: '1rem 0.5rem', textAlign: 'center' }}>Confianza</th>
                <th style={{ padding: '1rem 0.5rem', textAlign: 'center' }}>Acción</th>
              </tr>
            </thead>
            <tbody>
              {paginatedEvents.map((ev) => (
                <tr key={ev.id} style={{ borderBottom: '1px solid var(--border-color)' }}>
                  <td style={{ padding: '1rem 0.5rem', fontWeight: 600, fontSize: '1.125rem', letterSpacing: '1px', textAlign: 'center' }}>{ev.plate}</td>
                  <td style={{ padding: '1rem 0.5rem', textAlign: 'center' }}>
                    {ev.type === 'in' 
                      ? <span className="badge badge-success"><ArrowRight size={14} style={{ marginRight: '4px' }} /> Ingreso</span>
                      : <span className="badge badge-warning"><ArrowLeft size={14} style={{ marginRight: '4px' }} /> Salida</span>
                    }
                  </td>
                  <td style={{ padding: '1rem 0.5rem', color: 'var(--text-secondary)' }}>
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '0.25rem' }}>
                      <Clock size={14} /> {format(ev.timestamp, 'dd-MM-yyyy HH:mm:ss')}
                    </div>
                  </td>
                  <td style={{ padding: '1rem 0.5rem', textAlign: 'center' }}>
                    <div style={{ width: '100px', height: '6px', backgroundColor: 'var(--border-color)', borderRadius: '3px', overflow: 'hidden', margin: '0 auto' }}>
                      <div style={{ height: '100%', width: `${ev.confidence * 100}%`, backgroundColor: ev.confidence > 0.9 ? 'var(--status-success)' : 'var(--status-warning)' }}></div>
                    </div>
                    <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginTop: '4px', display: 'block', textAlign: 'center' }}>{(ev.confidence * 100).toFixed(1)}%</span>
                  </td>
                  <td style={{ padding: '1rem 0.5rem', textAlign: 'center' }}>
                    <button 
                      className="btn btn-secondary" 
                      style={{ padding: '0.25rem 0.75rem', fontSize: '0.75rem' }}
                      onClick={() => handleOpenModal(ev)}
                    >
                      Reportar Incidencia
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

        {/* Pagination Controls */}
        {filteredEvents.length > 0 && (
          <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', marginTop: '1.5rem', justifyContent: 'space-between', flexWrap: 'wrap', borderTop: '1px solid var(--border-color)', paddingTop: '1.25rem' }}>
            <div style={{ fontSize: '0.875rem', color: 'var(--text-secondary)' }}>
              Mostrando {Math.min(totalItems, (currentPage - 1) * pageSize + 1)} - {Math.min(totalItems, currentPage * pageSize)} de {totalItems} registros
            </div>
            <div style={{ display: 'flex', gap: '0.5rem' }}>
              <button 
                className="btn btn-secondary" 
                onClick={() => setCurrentPage(prev => Math.max(1, prev - 1))}
                disabled={currentPage === 1}
                style={{ padding: '0.5rem 1rem' }}
              >
                Anterior
              </button>
              <div style={{ display: 'flex', alignItems: 'center', padding: '0 0.5rem', fontSize: '0.875rem', fontWeight: 500 }}>
                Página {currentPage} de {totalPages}
              </div>
              <button 
                className="btn btn-secondary" 
                onClick={() => setCurrentPage(prev => Math.min(totalPages, prev + 1))}
                disabled={currentPage === totalPages}
                style={{ padding: '0.5rem 1rem' }}
              >
                Siguiente
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Modal para Reportar Incidencia */}
      {isModalOpen && selectedEvent && (
        <div style={modalOverlayStyle}>
          <div style={modalContentStyle} className="animate-fade-in">
            <div className="flex-between" style={{ marginBottom: '1.5rem', borderBottom: '1px solid var(--border-color)', paddingBottom: '1rem' }}>
              <h3 style={{ fontSize: '1.25rem', fontWeight: 600 }}>Reportar Incidencia</h3>
              <button onClick={() => setIsModalOpen(false)} style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text-secondary)' }}>
                <X size={20} />
              </button>
            </div>
            
            <form onSubmit={handleReportIncident} style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
              <div>
                <label style={{ display: 'block', fontSize: '0.875rem', fontWeight: 500, marginBottom: '0.25rem' }}>Vehículo Seleccionado</label>
                <p style={{ fontSize: '1.125rem', fontWeight: 700, letterSpacing: '1px', margin: 0, color: 'var(--text-primary)' }}>
                  {selectedEvent.plate}
                </p>
              </div>

              <div>
                <label style={{ display: 'block', fontSize: '0.875rem', fontWeight: 500, marginBottom: '0.5rem' }}>Tipo de Incidencia *</label>
                <select 
                  className="input-field"
                  value={incidentType}
                  onChange={(e) => setIncidentType(e.target.value)}
                  required
                >
                  <option value="Vehículo mal estacionado">Vehículo mal estacionado</option>
                  <option value="Vehículo con problema menor">Vehículo con problema menor</option>
                  <option value="Obstáculo en vía">Obstáculo en vía</option>
                  <option value="Otro">Otro</option>
                </select>
              </div>
              
              <div>
                <label style={{ display: 'block', fontSize: '0.875rem', fontWeight: 500, marginBottom: '0.5rem' }}>Detalles / Descripción *</label>
                <textarea 
                  className="input-field" 
                  rows="3"
                  placeholder="Detalles sobre por qué se reporta esta incidencia..."
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  required
                />
              </div>
              
              <div style={{ display: 'flex', gap: '1rem', justifyContent: 'flex-end', marginTop: '1rem' }}>
                <button type="button" className="btn btn-secondary" onClick={() => setIsModalOpen(false)}>Cancelar</button>
                <button type="submit" className="btn btn-primary" disabled={submitting}>
                  {submitting ? 'Enviando...' : 'Reportar'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
