-- Contrato de referencia 1.0.0; SQLite >= 3.37.
-- Activar foreign_keys en CADA conexion.
PRAGMA foreign_keys=ON;
CREATE TABLE schema_version (version TEXT PRIMARY KEY) STRICT;
INSERT INTO schema_version VALUES ('1.0.0');
CREATE TABLE snapshots (
 id TEXT PRIMARY KEY,
 version TEXT NOT NULL,
 naturaleza TEXT NOT NULL CHECK(naturaleza IN ('real','sintetico')),
 fecha_corte_utc TEXT NOT NULL,
 descripcion TEXT NOT NULL
) STRICT;

CREATE TABLE fuentes (
 snapshot_id TEXT NOT NULL,
 id TEXT NOT NULL,
 nombre TEXT NOT NULL,
 familia TEXT NOT NULL CHECK(familia IN ('noticias','indicadores')),
 url TEXT NOT NULL,
 condiciones TEXT NOT NULL,
 fecha_extraccion TEXT NOT NULL,
 PRIMARY KEY(snapshot_id,id),
 FOREIGN KEY(snapshot_id) REFERENCES snapshots(id),
 CHECK(length(id)>0)
) STRICT;

CREATE TABLE noticias (
 snapshot_id TEXT NOT NULL,
 id TEXT NOT NULL,
 fuente_id TEXT NOT NULL,
 titulo TEXT NOT NULL,
 url TEXT NOT NULL,
 medio TEXT NOT NULL,
 idioma TEXT NOT NULL,
 fecha_publicacion TEXT,
 fecha_deteccion TEXT,
 fecha_extraccion TEXT NOT NULL,
 tema TEXT NOT NULL CHECK(tema IN ('economia','logistica_canal','turismo','servicios_publicos','eventos_naturales','regulacion','sin_clasificar')),
 origen TEXT,
 alcance_texto TEXT NOT NULL CHECK(alcance_texto IN ('titular_metadatos','extracto_autorizado','texto_autorizado')),
 texto_disponible TEXT,
 PRIMARY KEY(snapshot_id,id),
 FOREIGN KEY(snapshot_id) REFERENCES snapshots(id),
 FOREIGN KEY(snapshot_id,fuente_id) REFERENCES fuentes(snapshot_id,id),
 UNIQUE(snapshot_id,url),
 CHECK(length(id)>0)
) STRICT;

CREATE TABLE indicadores (
 snapshot_id TEXT NOT NULL,
 id TEXT NOT NULL,
 fuente_id TEXT NOT NULL,
 pais_iso3 TEXT NOT NULL CHECK(length(pais_iso3)=3),
 indicador_id TEXT NOT NULL,
 anio INTEGER NOT NULL,
 valor REAL,
 unidad TEXT NOT NULL,
 fuente_url TEXT NOT NULL,
 fecha_extraccion TEXT NOT NULL,
 licencia TEXT NOT NULL,
 PRIMARY KEY(snapshot_id,id),
 FOREIGN KEY(snapshot_id) REFERENCES snapshots(id),
 FOREIGN KEY(snapshot_id,fuente_id) REFERENCES fuentes(snapshot_id,id),
 UNIQUE(snapshot_id,pais_iso3,indicador_id,anio),
 CHECK(length(id)>0)
) STRICT;

CREATE TABLE grupos (
 snapshot_id TEXT NOT NULL,
 id TEXT NOT NULL,
 tema TEXT NOT NULL,
 descripcion TEXT NOT NULL,
 PRIMARY KEY(snapshot_id,id),
 FOREIGN KEY(snapshot_id) REFERENCES snapshots(id),
 CHECK(length(id)>0)
) STRICT;

CREATE TABLE grupo_noticias (
 snapshot_id TEXT NOT NULL, grupo_id TEXT NOT NULL, noticia_id TEXT NOT NULL,
 procedencia_id TEXT, justificacion_procedencia TEXT,
 PRIMARY KEY(snapshot_id,grupo_id,noticia_id),
 FOREIGN KEY(snapshot_id,grupo_id) REFERENCES grupos(snapshot_id,id), FOREIGN KEY(snapshot_id,noticia_id) REFERENCES noticias(snapshot_id,id),
 CHECK(procedencia_id IS NULL OR (length(procedencia_id)>0 AND justificacion_procedencia IS NOT NULL AND length(justificacion_procedencia)>0))
) STRICT;
CREATE TABLE evidencias (
 snapshot_id TEXT NOT NULL,
 id TEXT NOT NULL,
 noticia_id TEXT,
 indicador_registro_id TEXT,
 campo TEXT NOT NULL,
 limitaciones TEXT NOT NULL,
 PRIMARY KEY(snapshot_id,id),
 FOREIGN KEY(snapshot_id) REFERENCES snapshots(id),
 FOREIGN KEY(snapshot_id,noticia_id) REFERENCES noticias(snapshot_id,id),
 FOREIGN KEY(snapshot_id,indicador_registro_id) REFERENCES indicadores(snapshot_id,id),
 CHECK((noticia_id IS NOT NULL)+(indicador_registro_id IS NOT NULL)=1),
 CHECK(length(id)>0)
) STRICT;

CREATE TABLE casos (
 snapshot_id TEXT NOT NULL,
 id TEXT NOT NULL,
 grupo_id TEXT,
 modalidad TEXT NOT NULL CHECK(modalidad='editorial'),
 titulo TEXT NOT NULL,
 estado_evidencia TEXT NOT NULL CHECK(estado_evidencia IN ('insuficiente','parcial','suficiente_para_borrador')),
 preguntas_pendientes TEXT NOT NULL,
 PRIMARY KEY(snapshot_id,id),
 FOREIGN KEY(snapshot_id) REFERENCES snapshots(id),
 FOREIGN KEY(snapshot_id,grupo_id) REFERENCES grupos(snapshot_id,id),
 CHECK(length(id)>0)
) STRICT;

CREATE TABLE caso_evidencias (
 snapshot_id TEXT NOT NULL, caso_id TEXT NOT NULL, evidencia_id TEXT NOT NULL,
 PRIMARY KEY(snapshot_id,caso_id,evidencia_id),
 FOREIGN KEY(snapshot_id,caso_id) REFERENCES casos(snapshot_id,id), FOREIGN KEY(snapshot_id,evidencia_id) REFERENCES evidencias(snapshot_id,id)
) STRICT;
CREATE TABLE priorizaciones (
 snapshot_id TEXT NOT NULL,
 id TEXT NOT NULL,
 caso_id TEXT NOT NULL,
 reglas_version TEXT NOT NULL,
 componentes_json TEXT NOT NULL,
 pesos_json TEXT NOT NULL,
 puntaje REAL NOT NULL CHECK(puntaje>=0 AND puntaje<=100),
 explicacion TEXT NOT NULL,
 fecha_utc TEXT NOT NULL,
 PRIMARY KEY(snapshot_id,id),
 FOREIGN KEY(snapshot_id) REFERENCES snapshots(id),
 FOREIGN KEY(snapshot_id,caso_id) REFERENCES casos(snapshot_id,id),
 CHECK(length(id)>0)
) STRICT;

CREATE TABLE borradores (
 snapshot_id TEXT NOT NULL,
 id TEXT NOT NULL,
 caso_id TEXT NOT NULL,
 version INTEGER NOT NULL CHECK(version>0),
 titulo TEXT NOT NULL,
 enfoque TEXT NOT NULL,
 brief TEXT NOT NULL,
 guion TEXT NOT NULL,
 copy TEXT NOT NULL,
 preguntas_json TEXT NOT NULL,
 alcance_texto TEXT NOT NULL,
 generador TEXT NOT NULL,
 modelo_version TEXT,
 prompt_version TEXT,
 fecha_utc TEXT NOT NULL,
 PRIMARY KEY(snapshot_id,id),
 FOREIGN KEY(snapshot_id) REFERENCES snapshots(id),
 FOREIGN KEY(snapshot_id,caso_id) REFERENCES casos(snapshot_id,id),
 UNIQUE(snapshot_id,caso_id,version),
 UNIQUE(snapshot_id,caso_id,id),
 CHECK(length(id)>0)
) STRICT;

CREATE TABLE afirmaciones (
 snapshot_id TEXT NOT NULL,
 id TEXT NOT NULL,
 caso_id TEXT NOT NULL,
 borrador_id TEXT NOT NULL,
 seccion TEXT NOT NULL CHECK(seccion IN ('titulo','enfoque','brief','guion','copy')),
 texto TEXT NOT NULL,
 tipo TEXT NOT NULL CHECK(tipo IN ('hecho','declaracion','inferencia','hipotesis')),
 PRIMARY KEY(snapshot_id,id),
 FOREIGN KEY(snapshot_id) REFERENCES snapshots(id),
 FOREIGN KEY(snapshot_id,caso_id,borrador_id) REFERENCES borradores(snapshot_id,caso_id,id),
 UNIQUE(snapshot_id,caso_id,id),
 CHECK(length(id)>0)
) STRICT;

CREATE TABLE citas (
 snapshot_id TEXT NOT NULL, caso_id TEXT NOT NULL, afirmacion_id TEXT NOT NULL,
 evidencia_id TEXT NOT NULL,
 relacion TEXT NOT NULL CHECK(relacion IN ('sustenta','contradice','contextualiza')),
 explicacion TEXT NOT NULL,
 PRIMARY KEY(snapshot_id,afirmacion_id,evidencia_id,relacion),
 FOREIGN KEY(snapshot_id,caso_id,afirmacion_id) REFERENCES afirmaciones(snapshot_id,caso_id,id),
 FOREIGN KEY(snapshot_id,caso_id,evidencia_id) REFERENCES caso_evidencias(snapshot_id,caso_id,evidencia_id)
) STRICT;
CREATE TABLE revisiones (
 snapshot_id TEXT NOT NULL,
 id TEXT NOT NULL,
 caso_id TEXT NOT NULL,
 borrador_id TEXT,
 secuencia INTEGER NOT NULL CHECK(secuencia>0),
 persona_revisora TEXT NOT NULL CHECK(length(trim(persona_revisora))>0),
 estado TEXT NOT NULL CHECK(estado IN ('en_revision','requiere_evidencia','aprobado_como_borrador','descartado')),
 comentario TEXT NOT NULL,
 fecha_utc TEXT NOT NULL,
 PRIMARY KEY(snapshot_id,id),
 FOREIGN KEY(snapshot_id) REFERENCES snapshots(id),
 FOREIGN KEY(snapshot_id,caso_id) REFERENCES casos(snapshot_id,id),
 FOREIGN KEY(snapshot_id,caso_id,borrador_id) REFERENCES borradores(snapshot_id,caso_id,id),
 UNIQUE(snapshot_id,caso_id,secuencia),
 CHECK(estado<>'aprobado_como_borrador' OR borrador_id IS NOT NULL),
 CHECK(length(id)>0)
) STRICT;

CREATE TRIGGER revisiones_no_update BEFORE UPDATE ON revisiones BEGIN SELECT RAISE(ABORT,'Insertar nueva revision; historial inmutable'); END;
CREATE TRIGGER revisiones_no_delete BEFORE DELETE ON revisiones BEGIN SELECT RAISE(ABORT,'Historial inmutable'); END;
CREATE TRIGGER revisiones_secuencia BEFORE INSERT ON revisiones
WHEN NEW.secuencia <> COALESCE((SELECT MAX(secuencia) FROM revisiones WHERE snapshot_id=NEW.snapshot_id AND caso_id=NEW.caso_id),0)+1
BEGIN SELECT RAISE(ABORT,'Secuencia de revision no consecutiva'); END;
CREATE VIEW estado_casos AS
SELECT c.snapshot_id,c.id,COALESCE((SELECT r.estado FROM revisiones r WHERE r.snapshot_id=c.snapshot_id AND r.caso_id=c.id ORDER BY r.secuencia DESC LIMIT 1),'nuevo') AS estado_revision FROM casos c;
CREATE VIEW procedencias_grupos AS
SELECT snapshot_id,grupo_id,COUNT(*) AS publicaciones,
COUNT(DISTINCT procedencia_id) AS procedencias_identificadas,
SUM(CASE WHEN procedencia_id IS NULL THEN 1 ELSE 0 END) AS publicaciones_origen_desconocido
FROM grupo_noticias GROUP BY snapshot_id,grupo_id;
CREATE INDEX noticias_tema ON noticias(snapshot_id,tema);
CREATE INDEX citas_evidencia ON citas(snapshot_id,evidencia_id);
