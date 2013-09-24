-- Table: bins

-- DROP TABLE bins;

CREATE TABLE bins
(
  lid text,
  sample_time timestamp with time zone,
  skip boolean default false
)
WITH (
  OIDS=FALSE
);

-- Index: ix_bins_lid

-- DROP INDEX ix_bins_lid;

CREATE INDEX ix_bins_lid
  ON bins
  USING hash
  (lid COLLATE pg_catalog."default" );

-- Index: ix_bins_lid_order

-- DROP INDEX ix_bins_lid_order;

CREATE INDEX ix_bins_lid_order
  ON bins
  USING btree
  (lid COLLATE pg_catalog."default" );

-- Index: ix_bins_sample_time

-- DROP INDEX ix_bins_sample_time;

CREATE INDEX ix_bins_sample_time
  ON bins
  USING btree
  (sample_time );

-- Table: bin_props

CREATE TABLE bin_props
(
  lid text primary key,
  lat float,
  lon float,
  description text
);

-- Table: fixity

-- DROP TABLE fixity;

CREATE TABLE fixity
(
  lid text,
  length integer,
  filename text,
  filetype text,
  sha1 text,
  fix_time timestamp with time zone,
  local_path text
)
WITH (
  OIDS=FALSE
);

-- Index: ix_fixity_length

-- DROP INDEX ix_fixity_length;

CREATE INDEX ix_fixity_length
  ON fixity
  USING btree
  (length );

-- Index: ix_fixity_lid

-- DROP INDEX ix_fixity_lid;

CREATE INDEX ix_fixity_lid
  ON fixity
  USING hash
  (lid COLLATE pg_catalog."default" );

-- Index: ix_fixity_sha1

-- DROP INDEX ix_fixity_sha1;

CREATE INDEX ix_fixity_sha1
  ON fixity
  USING hash
  (sha1 COLLATE pg_catalog."default" );