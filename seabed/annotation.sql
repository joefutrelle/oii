
-- database structure for prototype annotation tool
-- some columns due to be removed
-- load to postgresql with something like
-- psql -U seabed -d seabed -f annotation.sql

CREATE TABLE annotations (
    annotation_id text NOT NULL,
    image_id text,
    scope_id integer,
    category_id text,
    geometry_text text,
    thegeom geometry,
    annotator_id text,
    assignment_id text,
    "timestamp" timestamp with time zone,
    class_id integer,
    deprecated boolean DEFAULT false,
    geometry_id integer,
    imagename text,
    assignment_num integer
);


CREATE TABLE assignments (
    assignment_id integer NOT NULL,
    idmode text,
    site_description text,
    project_name text,
    priority text,
    initials text,
    idmode_id integer,
    added_timestamp timestamp with time zone,
    num_images integer,
    comment text,
    status text DEFAULT 'ready'::text,
    tracknum integer,
    startimage text,
    stopimage text,
    subsample text,
    date text,
    """time""" text
);


CREATE SEQUENCE assignments_assignment_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

CREATE TABLE classes (
    class_id integer NOT NULL,
    class_name text,
    old_idcode integer,
    facet_id integer,
    deprecated boolean DEFAULT false
);


CREATE SEQUENCE classes_class_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


CREATE TABLE facets (
    facet_id integer NOT NULL,
    facet_name text,
    scope_id integer,
    deprecated boolean DEFAULT false
);



CREATE TABLE geometries (
    geometry_id text,
    annotation_id text,
    deprecated boolean
);


CREATE TABLE idmodes (
    idmode_id integer NOT NULL,
    idmode_name text,
    class_id integer,
    deprecated boolean DEFAULT false
);


CREATE SEQUENCE idmodes_idmode_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

CREATE TABLE image_metadata (
    imagename text NOT NULL,
    camera text,
    alt1 numeric(12,2),
    alt2 numeric(12,2),
    alt_best numeric(12,2),
    vehicle_depth numeric(7,2),
    heading numeric(7,2),
    pitch numeric(7,2),
    roll numeric(7,2),
    bottom_depth numeric(7,2),
    temp numeric(7,3),
    sal numeric(7,3),
    lat numeric(10,6),
    lon numeric(11,6),
    speed numeric(6,2),
    cruise_id text,
    "timestamp" timestamp with time zone,
    thegeom geometry,
    fov numeric(15,3),
    depth_m numeric(7,2),
    serial_id integer,
    mm_px numeric(10,3),
    CONSTRAINT enforce_dims_thegeom CHECK ((st_ndims(thegeom) = 2)),
    CONSTRAINT enforce_geotype_thegeom CHECK (((geometrytype(thegeom) = 'POINT'::text) OR (thegeom IS NULL))),
    CONSTRAINT enforce_srid_thegeom CHECK ((st_srid(thegeom) = 4326))
);


CREATE SEQUENCE image_metadata_serial_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


CREATE TABLE imagelist (
    assignment_id integer,
    imagename text,
    status text DEFAULT 'new'::text,
    "offset" integer,
    imagelist_id integer NOT NULL
);


CREATE SEQUENCE imagelist_imagelist_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


CREATE TABLE scopes (
    scope_id integer NOT NULL,
    scope_name text,
    deprecated boolean DEFAULT false
);


CREATE SEQUENCE scopes_scope_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE assignments ALTER COLUMN assignment_id SET DEFAULT nextval('assignments_assignment_id_seq'::regclass);
ALTER TABLE classes ALTER COLUMN class_id SET DEFAULT nextval('classes_class_id_seq'::regclass);
ALTER TABLE idmodes ALTER COLUMN idmode_id SET DEFAULT nextval('idmodes_idmode_id_seq'::regclass);
ALTER TABLE image_metadata ALTER COLUMN serial_id SET DEFAULT nextval('image_metadata_serial_id_seq'::regclass);
ALTER TABLE imagelist ALTER COLUMN imagelist_id SET DEFAULT nextval('imagelist_imagelist_id_seq'::regclass);
ALTER TABLE scopes ALTER COLUMN scope_id SET DEFAULT nextval('scopes_scope_id_seq'::regclass);
ALTER TABLE ONLY annotations
    ADD CONSTRAINT annotations_pkey PRIMARY KEY (annotation_id);
ALTER TABLE ONLY assignments
    ADD CONSTRAINT assignments_pkey PRIMARY KEY (assignment_id);
ALTER TABLE ONLY classes
    ADD CONSTRAINT classes_pkey PRIMARY KEY (class_id);
ALTER TABLE ONLY image_metadata
    ADD CONSTRAINT image_metadata_pkey PRIMARY KEY (imagename);
