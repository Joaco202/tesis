import React, { useState, useEffect } from 'react';
import { Car, ArrowRight, ArrowLeft, Clock, Search, X, Eye, Camera, Plus } from 'lucide-react';
import { format } from 'date-fns';
import { es } from 'date-fns/locale';
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
  const [filterMode, setFilterMode] = useState('all'); // 'all' | 'inside'
  const [zones, setZones] = useState([]);
  const [selectedZoneId, setSelectedZoneId] = useState(null); // null = todas

  // Manual access registration states
  const [isManualModalOpen, setIsManualModalOpen] = useState(false);
  const [manualForm, setManualForm] = useState({
    patente: '',
    tipo: 'entrada', // 'entrada' | 'salida'
    zonaId: '',
  });
  const [submittingManual, setSubmittingManual] = useState(false);

  useEffect(() => {
    setCurrentPage(1);
  }, [search, pageSize]);

  const [isModalOpen, setIsModalOpen] = useState(false);
  const [selectedEvent, setSelectedEvent] = useState(null);
  const [incidentType, setIncidentType] = useState('Vehículo mal estacionado');
  const [description, setDescription] = useState('');
  const [incidentStatus, setIncidentStatus] = useState('abierta'); // 'abierta' = En proceso, 'cerrada' = Resuelto
  const [submitting, setSubmitting] = useState(false);

  const [isImageModalOpen, setIsImageModalOpen] = useState(false);
  const [selectedImageEvent, setSelectedImageEvent] = useState(null);
  const [zoomedImage, setZoomedImage] = useState(null);

  const handleOpenImageModal = (ev) => {
    setSelectedImageEvent(ev);
    setIsImageModalOpen(true);
  };

  // Cerrar modales con la tecla Escape
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === 'Escape') {
        setIsModalOpen(false);
        setIsImageModalOpen(false);
        setZoomedImage(null);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  // Fetch data function (explicita en el cuerpo del componente para poder llamarse tras acciones manuales)
  const fetchDashboardData = async () => {
    try {
      const startOfToday = new Date();
      startOfToday.setHours(0, 0, 0, 0);
      const todayIso = startOfToday.toISOString();

      // Fetch all zones
      const { data: allZones, error: zonesError } = await supabase
        .from('zonas')
        .select('id, nombre, capacidad')
        .eq('estado', true)
        .order('nombre');

      let defaultZoneId = null;
      if (!zonesError && allZones && allZones.length > 0) {
        setZones(allZones);
        const aulaMagna = allZones.find(z => z.nombre === 'Aula Magna');
        if (aulaMagna) {
          defaultZoneId = aulaMagna.id;
          setSelectedZoneId(prev => prev ?? aulaMagna.id);
          setOccupancy(prev => ({ ...prev, max: aulaMagna.capacidad }));
        } else {
          setOccupancy(prev => ({ ...prev, max: allZones[0].capacidad }));
        }
      }

      const { count, error: countError } = await supabase
        .from('accesos')
        .select('*', { count: 'exact', head: true })
        .is('fecha_salida', null);

      if (!countError && count !== null) {
        setOccupancy(prev => ({ ...prev, current: count }));
      }

      const { count: entriesCount, error: entriesError } = await supabase
        .from('accesos')
        .select('*', { count: 'exact', head: true })
        .gte('fecha_entrada', todayIso);

      if (!entriesError && entriesCount !== null) {
        setDailyTotals(prev => ({ ...prev, entries: entriesCount }));
      }

      const { count: exitsCount, error: exitsError } = await supabase
        .from('accesos')
        .select('*', { count: 'exact', head: true })
        .gte('fecha_salida', todayIso);

      if (!exitsError && exitsCount !== null) {
        setDailyTotals(prev => ({ ...prev, exits: exitsCount }));
      }

      const { data, error: dataError } = await supabase
        .from('accesos')
        .select('id, vehiculo_patente, fecha_entrada, fecha_salida, confianza_ocr, zona_id, imagen_origen, imagen_origen_salida')
        .order('fecha_entrada', { ascending: false })
        .limit(500);

      if (!dataError && data) {
        let timeline = [];
        data.forEach(row => {
          if (row.fecha_entrada) {
            timeline.push({
              id: row.id + '-in',
              accessId: row.id,
              zoneId: row.zona_id,
              plate: row.vehiculo_patente,
              type: 'in',
              timestamp: new Date(row.fecha_entrada),
              confidence: row.confianza_ocr || 0.95,
              imagen_origen: row.imagen_origen,
              imagen_origen_salida: row.imagen_origen_salida,
              fecha_salida: row.fecha_salida
            });
          }

          if (row.fecha_salida) {
            timeline.push({
              id: row.id + '-out',
              accessId: row.id,
              zoneId: row.zona_id,
              plate: row.vehiculo_patente,
              type: 'out',
              timestamp: new Date(row.fecha_salida),
              confidence: row.confianza_ocr || 0.95,
              imagen_origen: row.imagen_origen,
              imagen_origen_salida: row.imagen_origen_salida,
              fecha_salida: row.fecha_salida
            });
          }
        });

        timeline.sort((a, b) => b.timestamp - a.timestamp);
        setEvents(timeline);
      }
    } catch (err) {
      console.error('Error fetching guard dashboard data:', err);
    }
  };

  useEffect(() => {
    fetchDashboardData();

    const channel = supabase.channel('guard:accesos')
      .on('postgres_changes', { event: '*', schema: 'public', table: 'accesos' }, () => {
        fetchDashboardData();
      })
      .subscribe();

    return () => {
      supabase.removeChannel(channel);
    };
  }, []);

  const handleOpenManualModal = () => {
    setManualForm({
      patente: '',
      tipo: 'entrada',
      zonaId: selectedZoneId ? selectedZoneId.toString() : (zones[0]?.id?.toString() || ''),
    });
    setIsManualModalOpen(true);
  };

  const handleManualRegister = async (e) => {
    e.preventDefault();
    if (!manualForm.patente.trim()) {
      alert('Por favor, ingresa una patente.');
      return;
    }
    if (!manualForm.zonaId) {
      alert('Por favor, selecciona un estacionamiento.');
      return;
    }

    const cleanPlate = manualForm.patente.trim().toUpperCase().replace(/[^A-Z0-9]/g, '');
    
    // Validar formato chileno (patentes de autos/motos antiguas y nuevas, e institucionales)
    const formatAutoOld = /^[A-Z]{2}\d{4}$/; // AA1234
    const formatAutoNew = /^[A-Z]{4}\d{2}$/; // AAAA12
    const formatMoto = /^[A-Z]{2,3}\d{2,3}$/; // AA123, AAA12, AAA123, etc.
    const formatCarabineros = /^(Z|M|RP|AP|B|C|CB|AG|A)\d{4}$/; // Z1234, RP1234, etc.
    
    const isValidChilean = formatAutoOld.test(cleanPlate) || 
                           formatAutoNew.test(cleanPlate) || 
                           formatMoto.test(cleanPlate) || 
                           formatCarabineros.test(cleanPlate);
    
    if (!isValidChilean) {
      alert('La patente no cumple con un formato chileno válido (ejemplos: AA1234, AAAA12, patentes de moto o patentes institucionales de Carabineros como RP1234, Z1234).');
      return;
    }

    setSubmittingManual(true);
    try {
      const { data: { user } } = await supabase.auth.getUser();

      // Asegurar que el vehículo esté registrado para evitar errores de Foreign Key
      const { error: vehError } = await supabase
        .from('vehiculos')
        .upsert({ patente: cleanPlate }, { onConflict: 'patente' });

      if (vehError) throw vehError;

      const selectedZoneInt = parseInt(manualForm.zonaId);
      const nowStr = new Date().toISOString();

      if (manualForm.tipo === 'entrada') {
        const { error: accError } = await supabase
          .from('accesos')
          .insert([{
            vehiculo_patente: cleanPlate,
            zona_id: selectedZoneInt,
            camera_id: 'Registro Manual',
            fecha_entrada: nowStr,
            confianza_ocr: 1.0,
            creado_por: user ? user.id : null,
          }]);

        if (accError) throw accError;
        alert('Ingreso manual registrado con éxito.');
      } else {
        // Salida
        const { data: openAccesses, error: fetchError } = await supabase
          .from('accesos')
          .select('id')
          .eq('vehiculo_patente', cleanPlate)
          .eq('zona_id', selectedZoneInt)
          .is('fecha_salida', null)
          .order('fecha_entrada', { ascending: false })
          .limit(1);

        if (fetchError) throw fetchError;

        if (openAccesses && openAccesses.length > 0) {
          // Actualizar acceso abierto existente
          const { error: accError } = await supabase
            .from('accesos')
            .update({
              fecha_salida: nowStr,
              camera_salida_id: 'Registro Manual',
              confianza_ocr_salida: 1.0
            })
            .eq('id', openAccesses[0].id);

          if (accError) throw accError;
          alert('Salida manual registrada con éxito (se cerró el ingreso previo).');
        } else {
          // Registrar salida huérfana
          const { error: accError } = await supabase
            .from('accesos')
            .insert([{
              vehiculo_patente: cleanPlate,
              zona_id: selectedZoneInt,
              camera_salida_id: 'Registro Manual',
              fecha_salida: nowStr,
              confianza_ocr_salida: 1.0,
              creado_por: user ? user.id : null,
            }]);

          if (accError) throw accError;
          alert('Salida manual registrada con éxito (sin entrada previa asociada).');
        }
      }

      setIsManualModalOpen(false);
      fetchDashboardData();
    } catch (err) {
      console.error('Error al registrar acceso manual:', err);
      alert('Error al registrar acceso manual: ' + err.message);
    } finally {
      setSubmittingManual(false);
    }
  };

  useEffect(() => {
    const interval = setInterval(() => {
      setCurrentTime(new Date());
    }, 1000);
    return () => clearInterval(interval);
  }, []);

  // Cerrar modales al presionar la tecla Escape
  useEffect(() => {
    const handleKeyDown = (event) => {
      if (event.key === 'Escape') {
        if (zoomedImage) {
          setZoomedImage(null);
        } else if (isImageModalOpen) {
          setIsImageModalOpen(false);
        }
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => {
      window.removeEventListener('keydown', handleKeyDown);
    };
  }, [zoomedImage, isImageModalOpen]);

  const filteredEvents = events.filter(e => {
    // Filtro por patente
    if (search && !e.plate.toLowerCase().includes(search.toLowerCase())) return false;
    // Filtro por zona
    if (selectedZoneId !== null && e.zoneId !== selectedZoneId) return false;
    // Filtro por tipo de movimiento (in / out / all)
    if (filterMode === 'in') return e.type === 'in';
    if (filterMode === 'out') return e.type === 'out';
    return true;
  });
  const totalItems = filteredEvents.length;
  const totalPages = Math.ceil(totalItems / pageSize) || 1;
  const paginatedEvents = filteredEvents.slice((currentPage - 1) * pageSize, currentPage * pageSize);

  const handleOpenModal = (ev) => {
    setSelectedEvent(ev);
    setIncidentType('Vehículo mal estacionado');
    setDescription('');
    setIncidentStatus('abierta'); // por defecto "En proceso"
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
        estado: incidentStatus,
      };

      const { error } = await supabase
        .from('incidencias')
        .insert([newInc]);

      if (error) throw error;

      alert('Incidencia registrada exitosamente.');
      setIsModalOpen(false);
      setSelectedEvent(null);
      setDescription('');
      setIncidentType('Vehículo mal estacionado');
      setIncidentStatus('abierta');
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

  const radius = 52;
  const circumference = 2 * Math.PI * radius;
  const clampedPercentage = Math.min(100, Math.max(0, occupancyPercentage));
  const strokeDashoffset = circumference - (clampedPercentage / 100) * circumference;

  return (
    <>
      <div className="animate-fade-in">
        <div className="flex-between" style={{ marginBottom: '2rem', flexWrap: 'wrap', gap: '1rem' }}>
          <div>
            <h1 style={{ fontSize: '1.75rem', fontWeight: 700, color: 'var(--text-primary)' }}>Panel de Control</h1>
            <p style={{ color: 'var(--text-secondary)' }}>Monitoreo del Aula Magna</p>
          </div>
          <div style={{ display: 'flex', gap: '1.5rem', alignItems: 'center', flexWrap: 'wrap' }}>
            <button 
              className="btn btn-primary" 
              onClick={handleOpenManualModal}
              style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', height: '42px' }}
            >
              <Plus size={18} /> Registrar Acceso Manual
            </button>
            <div style={{ textAlign: 'right' }}>
              <p style={{ fontSize: '0.875rem', color: 'var(--text-secondary)' }}>{format(currentTime, "dd 'de' MMMM, yyyy", { locale: es })}</p>
              <p style={{ fontSize: '1.25rem', fontWeight: 600 }}>{format(currentTime, "HH:mm:ss")}</p>
            </div>
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
          <div style={{ marginBottom: '1.5rem' }}>
            <div className="flex-between" style={{ flexWrap: 'wrap', gap: '1rem', marginBottom: '1rem' }}>
              <div>
                <h2 style={{ fontSize: '1.25rem', fontWeight: 600 }}>Registro en Vivo (Cámara)</h2>
                {zones.length > 0 && (
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginTop: '0.4rem' }}>
                    <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>Estacionamiento:</span>
                    <div style={{ display: 'flex', gap: '0.35rem', flexWrap: 'wrap' }}>
                      {zones.map(z => (
                        <button
                          key={z.id}
                          onClick={() => { setSelectedZoneId(z.id); setCurrentPage(1); }}
                          style={{
                            padding: '0.2rem 0.7rem',
                            borderRadius: '9999px',
                            border: '1px solid',
                            fontSize: '0.75rem',
                            fontWeight: 600,
                            cursor: 'pointer',
                            transition: 'all 0.2s',
                            borderColor: selectedZoneId === z.id ? 'var(--ubb-blue)' : 'var(--border-color)',
                            backgroundColor: selectedZoneId === z.id ? 'var(--ubb-blue)' : 'transparent',
                            color: selectedZoneId === z.id ? '#fff' : 'var(--text-secondary)',
                          }}
                        >
                          {z.nombre}
                        </button>
                      ))}
                    </div>
                  </div>
                )}
              </div>
              <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'center', flexWrap: 'wrap' }}>
                {/* Botón Tri-estado de Filtro de Movimientos */}
                <button
                  onClick={() => {
                    setFilterMode(prev => prev === 'all' ? 'in' : prev === 'in' ? 'out' : 'all');
                    setCurrentPage(1);
                  }}
                  style={{
                    padding: '0.35rem 1rem',
                    borderRadius: '9999px',
                    border: '1.5px solid',
                    fontSize: '0.8rem',
                    fontWeight: 600,
                    cursor: 'pointer',
                    transition: 'all 0.2s',
                    borderColor: 
                      filterMode === 'in' ? 'var(--status-success)' : 
                      filterMode === 'out' ? 'var(--ubb-orange)' : 
                      'var(--border-color)',
                    backgroundColor: 
                      filterMode === 'in' ? 'rgba(16, 185, 129, 0.1)' : 
                      filterMode === 'out' ? 'rgba(245, 158, 11, 0.1)' : 
                      'transparent',
                    color: 
                      filterMode === 'in' ? 'var(--status-success)' : 
                      filterMode === 'out' ? 'var(--ubb-orange)' : 
                      'var(--text-secondary)',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '0.4rem',
                  }}
                >
                  {filterMode === 'in' && <ArrowRight size={14} />}
                  {filterMode === 'out' && <ArrowLeft size={14} />}
                  {filterMode === 'all' && <Car size={14} />}
                  
                  {filterMode === 'in' ? 'Solo Ingresos' : 
                   filterMode === 'out' ? 'Solo Salidas' : 
                   'Movimientos (Todos)'}
                </button>
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
                    onChange={(e) => { setSearch(e.target.value); setCurrentPage(1); }}
                  />
                </div>
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
                      <div style={{ display: 'flex', gap: '0.5rem', justifyContent: 'center' }}>
                        <button
                          className="btn btn-secondary"
                          style={{ padding: '0.25rem 0.75rem', fontSize: '0.75rem' }}
                          onClick={() => handleOpenModal(ev)}
                        >
                          Reportar Incidencia
                        </button>
                        <button
                          className="btn btn-primary"
                          style={{ padding: '0.25rem 0.75rem', fontSize: '0.75rem', display: 'flex', alignItems: 'center', gap: '4px' }}
                          onClick={() => handleOpenImageModal(ev)}
                        >
                          <Eye size={14} /> Fotos
                        </button>
                      </div>
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
      </div>

      {/* Modal para Reportar Incidencia */}
      {isModalOpen && selectedEvent && (
        <div style={modalOverlayStyle} onClick={() => setIsModalOpen(false)}>
          <div style={modalContentStyle} className="animate-fade-in" onClick={(e) => e.stopPropagation()}>
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
                <label style={{ display: 'block', fontSize: '0.875rem', fontWeight: 500, marginBottom: '0.5rem' }}>Tipo de Incidencia</label>
                <select
                  className="input-field"
                  value={incidentType}
                  onChange={(e) => setIncidentType(e.target.value)}
                  required
                >
                  <option value="Vehículo mal estacionado">Vehículo mal estacionado</option>
                  <option value="Vehículo con problema menor">Vehículo con problema menor</option>
                  <option value="Vehículo con problema mayor">Vehículo con problema mayor</option>
                  <option value="Otro">Otro</option>
                </select>
              </div>

              <div>
                <label style={{ display: 'block', fontSize: '0.875rem', fontWeight: 500, marginBottom: '0.5rem' }}>Estado de la Incidencia</label>
                <select
                  className="input-field"
                  value={incidentStatus}
                  onChange={(e) => setIncidentStatus(e.target.value)}
                  required
                >
                  <option value="abierta">En proceso</option>
                  <option value="cerrada">Resuelto</option>
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

      {/* Modal para Ver Imágenes (Ingreso/Salida) */}
      {isImageModalOpen && selectedImageEvent && (
        <div style={modalOverlayStyle} onClick={() => setIsImageModalOpen(false)}>
          <div style={{ ...modalContentStyle, maxWidth: '700px' }} className="animate-fade-in" onClick={(e) => e.stopPropagation()}>
            <div className="flex-between" style={{ marginBottom: '1.5rem', borderBottom: '1px solid var(--border-color)', paddingBottom: '1rem' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <Camera size={20} color="var(--ubb-blue)" />
                <h3 style={{ fontSize: '1.25rem', fontWeight: 600, margin: 0 }}>
                  Imágenes de Registro: <span style={{ color: 'var(--text-primary)', letterSpacing: '1px' }}>{selectedImageEvent.plate}</span>
                </h3>
              </div>
              <button onClick={() => setIsImageModalOpen(false)} style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text-secondary)' }}>
                <X size={20} />
              </button>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1.5rem', marginBottom: '1.5rem' }}>
              {/* Columna Ingreso */}
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                <h4 style={{ fontSize: '0.875rem', fontWeight: 600, color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.5px', margin: 0, textAlign: 'center' }}>
                  Ingreso
                </h4>
                <div style={{
                  height: '240px',
                  backgroundColor: 'rgba(15, 23, 42, 0.4)',
                  borderRadius: 'var(--radius-md)',
                  border: '1px solid var(--border-color)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  overflow: 'hidden',
                  position: 'relative'
                }}>
                  {selectedImageEvent.imagen_origen ? (
                    <img
                      src={selectedImageEvent.imagen_origen}
                      alt="Ingreso de vehículo"
                      style={{ width: '100%', height: '100%', objectFit: 'contain', cursor: 'pointer' }}
                      onClick={() => setZoomedImage(selectedImageEvent.imagen_origen)}
                      onError={(e) => {
                        e.target.style.display = 'none';
                        e.target.parentNode.innerHTML = '<span style="color: var(--text-secondary); font-size: 0.875rem;">Error al cargar imagen</span>';
                      }}
                    />
                  ) : (
                    <div style={{ textAlign: 'center', color: 'var(--text-secondary)', padding: '1rem' }}>
                      <Car size={32} style={{ opacity: 0.3, marginBottom: '0.5rem', margin: '0 auto' }} />
                      <span style={{ fontSize: '0.875rem', display: 'block' }}>Sin imagen de ingreso</span>
                    </div>
                  )}
                </div>
              </div>

              {/* Columna Salida */}
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                <h4 style={{ fontSize: '0.875rem', fontWeight: 600, color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.5px', margin: 0, textAlign: 'center' }}>
                  Salida
                </h4>
                <div style={{
                  height: '240px',
                  backgroundColor: 'rgba(15, 23, 42, 0.4)',
                  borderRadius: 'var(--radius-md)',
                  border: '1px solid var(--border-color)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  overflow: 'hidden',
                  position: 'relative'
                }}>
                  {selectedImageEvent.imagen_origen_salida ? (
                    <img
                      src={selectedImageEvent.imagen_origen_salida}
                      alt="Salida de vehículo"
                      style={{ width: '100%', height: '100%', objectFit: 'contain', cursor: 'pointer' }}
                      onClick={() => setZoomedImage(selectedImageEvent.imagen_origen_salida)}
                      onError={(e) => {
                        e.target.style.display = 'none';
                        e.target.parentNode.innerHTML = '<span style="color: var(--text-secondary); font-size: 0.875rem;">Error al cargar imagen</span>';
                      }}
                    />
                  ) : (
                    <div style={{ textAlign: 'center', color: 'var(--text-secondary)', padding: '1rem' }}>
                      <Car size={32} style={{ opacity: 0.3, marginBottom: '0.5rem', margin: '0 auto' }} />
                      <span style={{ fontSize: '0.875rem', display: 'block' }}>
                        {selectedImageEvent.type === 'in' && !selectedImageEvent.fecha_salida
                          ? 'Vehículo no registra salida'
                          : 'Sin imagen de salida'}
                      </span>
                    </div>
                  )}
                </div>
              </div>
            </div>

            <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
              <button className="btn btn-secondary" onClick={() => setIsImageModalOpen(false)}>
                Cerrar
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Modal para Zoom de Imagen Completa */}
      {zoomedImage && (
        <div 
          style={{
            ...modalOverlayStyle,
            zIndex: 1100,
            backgroundColor: 'rgba(10, 15, 30, 0.9)',
          }}
          onClick={() => setZoomedImage(null)}
        >
          <div 
            style={{
              position: 'relative',
              maxWidth: '90vw',
              maxHeight: '90vh',
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              justifyContent: 'center',
            }}
            onClick={(e) => e.stopPropagation()}
          >
            <button 
              onClick={() => setZoomedImage(null)}
              style={{
                position: 'absolute',
                top: '-40px',
                right: '0',
                background: 'none',
                border: 'none',
                cursor: 'pointer',
                color: '#ffffff',
                display: 'flex',
                alignItems: 'center',
                gap: '0.25rem',
                fontSize: '0.875rem',
                fontWeight: 600,
              }}
            >
              <X size={20} /> Cerrar
            </button>
            <img 
              src={zoomedImage} 
              alt="Visualización completa" 
              style={{
                maxWidth: '100%',
                maxHeight: '80vh',
                objectFit: 'contain',
                borderRadius: 'var(--radius-md)',
                boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.7)',
              }} 
            />
          </div>
        </div>
      )}
      {/* Modal para Registrar Acceso Manual */}
      {isManualModalOpen && (
        <div style={modalOverlayStyle}>
          <div style={modalContentStyle} className="animate-fade-in">
            <div className="flex-between" style={{ marginBottom: '1.5rem', borderBottom: '1px solid var(--border-color)', paddingBottom: '1rem' }}>
              <h3 style={{ fontSize: '1.25rem', fontWeight: 600 }}>Registrar Acceso Manual</h3>
              <button onClick={() => setIsManualModalOpen(false)} style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text-secondary)' }}>
                <X size={20} />
              </button>
            </div>
            
            <form onSubmit={handleManualRegister} style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
              <div>
                <label style={{ display: 'block', fontSize: '0.875rem', fontWeight: 500, marginBottom: '0.5rem' }}>Patente *</label>
                <input
                  type="text"
                  className="input-field"
                  placeholder="Ej. ABCD12"
                  value={manualForm.patente}
                  onChange={(e) => setManualForm(prev => ({ ...prev, patente: e.target.value.toUpperCase() }))}
                  required
                  style={{ textTransform: 'uppercase', letterSpacing: '1px', fontSize: '1rem', fontWeight: 600 }}
                />
              </div>

              <div>
                <label style={{ display: 'block', fontSize: '0.875rem', fontWeight: 500, marginBottom: '0.5rem' }}>Tipo de Acceso *</label>
                <div style={{ display: 'flex', gap: '1.5rem' }}>
                  <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', cursor: 'pointer', fontSize: '0.9rem' }}>
                    <input
                      type="radio"
                      name="tipoAcceso"
                      value="entrada"
                      checked={manualForm.tipo === 'entrada'}
                      onChange={() => setManualForm(prev => ({ ...prev, tipo: 'entrada' }))}
                      style={{ cursor: 'pointer', width: '16px', height: '16px' }}
                    />
                    Ingreso
                  </label>
                  <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', cursor: 'pointer', fontSize: '0.9rem' }}>
                    <input
                      type="radio"
                      name="tipoAcceso"
                      value="salida"
                      checked={manualForm.tipo === 'salida'}
                      onChange={() => setManualForm(prev => ({ ...prev, tipo: 'salida' }))}
                      style={{ cursor: 'pointer', width: '16px', height: '16px' }}
                    />
                    Salida
                  </label>
                </div>
              </div>

              <div>
                <label style={{ display: 'block', fontSize: '0.875rem', fontWeight: 500, marginBottom: '0.5rem' }}>Estacionamiento *</label>
                <select
                  className="input-field"
                  value={manualForm.zonaId}
                  onChange={(e) => setManualForm(prev => ({ ...prev, zonaId: e.target.value }))}
                  required
                >
                  <option value="" disabled>Selecciona un estacionamiento</option>
                  {zones.map(z => (
                    <option key={z.id} value={z.id.toString()}>{z.nombre}</option>
                  ))}
                </select>
              </div>

              <div style={{ display: 'flex', gap: '1rem', justifyContent: 'flex-end', marginTop: '1.25rem' }}>
                <button type="button" className="btn btn-secondary" onClick={() => setIsManualModalOpen(false)}>Cancelar</button>
                <button type="submit" className="btn btn-primary" disabled={submittingManual}>
                  {submittingManual ? 'Registrando...' : 'Registrar Acceso'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </>
  );
};
