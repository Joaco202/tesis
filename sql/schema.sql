-- =========================================================
-- schema.sql
-- Sistema de gestión de estacionamiento + OCR de patentes
-- Compatible con PostgreSQL / Supabase
-- =========================================================

create extension if not exists pgcrypto;

-- =========================================================
-- TABLA: roles
-- =========================================================
create table if not exists public.roles (
    id bigserial primary key,
    nombre varchar(50) not null unique,
    descripcion text,
    created_at timestamptz not null default now()
);

comment on table public.roles is 'Roles del sistema.';
comment on column public.roles.nombre is 'Nombre único del rol: administrador, guardia, encargado, visitante.';

-- =========================================================
-- TABLA: usuarios
-- Si usas Supabase Auth, idealmente id = auth.users.id
-- =========================================================
create table if not exists public.usuarios (
    id uuid primary key default gen_random_uuid(),
    nombre varchar(120) not null,
    email varchar(120) not null unique,
    rol_id bigint not null references public.roles(id) on update cascade on delete restrict,
    estado boolean not null default true,
    created_at timestamptz not null default now()
);

comment on table public.usuarios is 'Usuarios del sistema.';
comment on column public.usuarios.rol_id is 'Rol asociado al usuario.';

-- =========================================================
-- TABLA: zonas
-- =========================================================
create table if not exists public.zonas (
    id bigserial primary key,
    nombre varchar(100) not null unique,
    descripcion text,
    capacidad integer not null check (capacidad >= 0),
    estado boolean not null default true,
    created_at timestamptz not null default now()
);

comment on table public.zonas is 'Zonas o sectores del estacionamiento.';
comment on column public.zonas.capacidad is 'Cantidad máxima de vehículos permitidos en la zona.';

-- =========================================================
-- TABLA: camaras
-- Relaciona cámara física con zona
-- =========================================================
create table if not exists public.camaras (
    id bigserial primary key,
    camera_id varchar(100) not null unique,
    nombre varchar(120),
    zona_id bigint references public.zonas(id) on update cascade on delete set null,
    tipo_evento_default varchar(20) check (tipo_evento_default in ('entrada', 'salida')),
    estado boolean not null default true,
    created_at timestamptz not null default now()
);

comment on table public.camaras is 'Cámaras configuradas para registrar accesos.';
comment on column public.camaras.camera_id is 'Identificador lógico usado por el pipeline OCR.';
comment on column public.camaras.tipo_evento_default is 'Tipo de evento esperado por defecto para la cámara.';

-- =========================================================
-- TABLA: vehiculos
-- =========================================================
create table if not exists public.vehiculos (
    patente varchar(10) primary key,
    tipo varchar(50),
    funcionario boolean not null default false,
    propietario_nombre varchar(120),
    observaciones text,
    created_at timestamptz not null default now()
);

comment on table public.vehiculos is 'Vehículos detectados o registrados.';
comment on column public.vehiculos.patente is 'Patente normalizada del vehículo.';

-- =========================================================
-- TABLA: accesos
-- Registra entradas y salidas
-- =========================================================
create table if not exists public.accesos (
    id bigserial primary key,
    vehiculo_patente varchar(10) not null references public.vehiculos(patente) on update cascade on delete restrict,
    zona_id bigint references public.zonas(id) on update cascade on delete set null,

    -- Evento inicial
    camera_id varchar(100) not null,
    fecha_entrada timestamptz,
    confianza_ocr double precision,
    imagen_origen text,

    -- Evento de cierre
    fecha_salida timestamptz,
    camera_salida_id varchar(100),
    confianza_ocr_salida double precision,
    imagen_origen_salida text,

    -- Metadatos
    creado_por uuid references public.usuarios(id) on update cascade on delete set null,
    created_at timestamptz not null default now(),

    constraint chk_accesos_al_menos_un_evento
        check (fecha_entrada is not null or fecha_salida is not null),

    constraint chk_accesos_fechas_validas
        check (
            fecha_entrada is null
            or fecha_salida is null
            or fecha_salida >= fecha_entrada
        )
);

comment on table public.accesos is 'Registro histórico de entradas y salidas de vehículos.';
comment on column public.accesos.zona_id is 'Zona del estacionamiento asociada al acceso.';
comment on column public.accesos.camera_id is 'Cámara que registró la entrada.';
comment on column public.accesos.camera_salida_id is 'Cámara que registró la salida.';
comment on column public.accesos.creado_por is 'Usuario que registró o supervisó el evento, si aplica.';

-- =========================================================
-- TABLA: incidencias
-- =========================================================
create table if not exists public.incidencias (
    id bigserial primary key,
    acceso_id bigint references public.accesos(id) on update cascade on delete set null,
    vehiculo_patente varchar(10) references public.vehiculos(patente) on update cascade on delete set null,
    zona_id bigint references public.zonas(id) on update cascade on delete set null,
    usuario_id uuid references public.usuarios(id) on update cascade on delete set null,

    tipo varchar(80) not null,
    descripcion text not null,
    estado varchar(30) not null default 'abierta'
        check (estado in ('abierta', 'en_revision', 'cerrada')),
    fecha_creacion timestamptz not null default now(),
    fecha_cierre timestamptz,

    constraint chk_incidencia_cierre
        check (
            fecha_cierre is null
            or fecha_cierre >= fecha_creacion
        )
);

comment on table public.incidencias is 'Incidencias relacionadas a accesos, vehículos o zonas.';
comment on column public.incidencias.tipo is 'Ejemplo: patente no reconocida, acceso bloqueado, error OCR.';
comment on column public.incidencias.estado is 'Estado actual de la incidencia.';

-- =========================================================
-- ÍNDICES
-- =========================================================
create index if not exists idx_usuarios_rol_id
    on public.usuarios (rol_id);

create index if not exists idx_camaras_zona_id
    on public.camaras (zona_id);

create index if not exists idx_accesos_patente
    on public.accesos (vehiculo_patente);

create index if not exists idx_accesos_zona_id
    on public.accesos (zona_id);

create index if not exists idx_accesos_fecha_entrada
    on public.accesos (fecha_entrada desc);

create index if not exists idx_accesos_fecha_salida
    on public.accesos (fecha_salida desc);

create index if not exists idx_accesos_camera_id
    on public.accesos (camera_id);

create index if not exists idx_accesos_abiertos
    on public.accesos (vehiculo_patente)
    where fecha_salida is null;

create index if not exists idx_incidencias_estado
    on public.incidencias (estado);

create index if not exists idx_incidencias_fecha_creacion
    on public.incidencias (fecha_creacion desc);

-- =========================================================
-- VISTA: accesos_abiertos
-- Vehículos actualmente dentro
-- =========================================================
create or replace view public.accesos_abiertos as
select
    a.id,
    a.vehiculo_patente,
    a.zona_id,
    z.nombre as zona_nombre,
    a.camera_id,
    a.fecha_entrada,
    a.confianza_ocr,
    a.imagen_origen,
    a.created_at
from public.accesos a
left join public.zonas z on z.id = a.zona_id
where a.fecha_entrada is not null
  and a.fecha_salida is null;

comment on view public.accesos_abiertos is 'Accesos abiertos: vehículos que aún no registran salida.';

-- =========================================================
-- VISTA: resumen_ocupacion_por_zona
-- =========================================================
create or replace view public.resumen_ocupacion_por_zona as
select
    z.id as zona_id,
    z.nombre as zona_nombre,
    z.capacidad,
    count(a.id)::integer as ocupados,
    greatest(z.capacidad - count(a.id)::integer, 0) as disponibles
from public.zonas z
left join public.accesos a
    on a.zona_id = z.id
   and a.fecha_entrada is not null
   and a.fecha_salida is null
group by z.id, z.nombre, z.capacidad
order by z.nombre;

comment on view public.resumen_ocupacion_por_zona is 'Ocupación actual por zona del estacionamiento.';

-- =========================================================
-- VISTA: resumen_ocupacion_total
-- =========================================================
create or replace view public.resumen_ocupacion_total as
select
    coalesce(sum(capacidad), 0)::integer as capacidad_total,
    coalesce(sum(ocupados), 0)::integer as ocupados_totales,
    coalesce(sum(disponibles), 0)::integer as disponibles_totales
from public.resumen_ocupacion_por_zona;

comment on view public.resumen_ocupacion_total is 'Resumen global de ocupación del estacionamiento.';

-- =========================================================
-- VISTA: dashboard_kpis
-- =========================================================
create or replace view public.dashboard_kpis as
select
    (select count(*)::integer from public.vehiculos) as total_vehiculos_registrados,
    (select count(*)::integer from public.accesos) as total_eventos_acceso,
    (select count(*)::integer from public.accesos where fecha_salida is null and fecha_entrada is not null) as vehiculos_actualmente_dentro,
    (select count(*)::integer from public.incidencias where estado <> 'cerrada') as incidencias_abiertas;

comment on view public.dashboard_kpis is 'Vista simple de KPIs generales para panel ejecutivo.';

-- =========================================================
-- DATOS INICIALES
-- =========================================================
insert into public.roles (nombre, descripcion)
values
    ('administrador', 'Administra configuración, usuarios y parámetros del sistema'),
    ('guardia', 'Supervisa accesos y monitorea ocupación'),
    ('encargado', 'Revisa reportes, estadísticas e incidencias'),
    ('visitante', 'Consulta disponibilidad del estacionamiento')
on conflict (nombre) do nothing;

-- Ejemplo de zonas
insert into public.zonas (nombre, descripcion, capacidad)
values
    ('Aula Magna', 'Zona principal de estacionamiento del Aula Magna', 50),
    ('Sector Norte', 'Zona norte del campus', 30)
on conflict (nombre) do nothing;

-- Ejemplo de cámaras
insert into public.camaras (camera_id, nombre, zona_id, tipo_evento_default)
select 'cam-acceso-1', 'Cámara Acceso Principal', z.id, 'entrada'
from public.zonas z
where z.nombre = 'Aula Magna'
on conflict (camera_id) do nothing;

insert into public.camaras (camera_id, nombre, zona_id, tipo_evento_default)
select 'cam-salida-1', 'Cámara Salida Principal', z.id, 'salida'
from public.zonas z
where z.nombre = 'Aula Magna'
on conflict (camera_id) do nothing;