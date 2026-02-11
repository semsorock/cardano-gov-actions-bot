-- DROP SCHEMA public;

CREATE SCHEMA public AUTHORIZATION postgres;

-- DROP DOMAIN public.addr29type;

CREATE DOMAIN public.addr29type AS bytea;
-- DROP TYPE public."anchortype";

CREATE TYPE public."anchortype" AS ENUM (
	'gov_action',
	'drep',
	'other',
	'vote',
	'committee_dereg',
	'constitution');

-- DROP DOMAIN public.asset32type;

CREATE DOMAIN public.asset32type AS bytea;
-- DROP TYPE public."govactiontype";

CREATE TYPE public."govactiontype" AS ENUM (
	'ParameterChange',
	'HardForkInitiation',
	'TreasuryWithdrawals',
	'NoConfidence',
	'NewCommittee',
	'NewConstitution',
	'InfoAction');

-- DROP DOMAIN public.hash28type;

CREATE DOMAIN public.hash28type AS bytea;
-- DROP DOMAIN public.hash32type;

CREATE DOMAIN public.hash32type AS bytea;
-- DROP DOMAIN public."int65type";

CREATE DOMAIN public."int65type" AS numeric(20,0);
-- DROP DOMAIN public."lovelace";

CREATE DOMAIN public."lovelace" AS numeric(20,0);
-- DROP DOMAIN public."outsum";

CREATE DOMAIN public."outsum" AS word128type;
-- DROP TYPE public."rewardtype";

CREATE TYPE public."rewardtype" AS ENUM (
	'leader',
	'member',
	'reserves',
	'treasury',
	'refund',
	'proposal_refund');

-- DROP TYPE public."scriptpurposetype";

CREATE TYPE public."scriptpurposetype" AS ENUM (
	'spend',
	'mint',
	'cert',
	'reward',
	'vote',
	'propose');

-- DROP TYPE public."scripttype";

CREATE TYPE public."scripttype" AS ENUM (
	'multisig',
	'timelock',
	'plutusV1',
	'plutusV2',
	'plutusV3');

-- DROP TYPE public."syncstatetype";

CREATE TYPE public."syncstatetype" AS ENUM (
	'lagging',
	'following');

-- DROP DOMAIN public."txindex";

CREATE DOMAIN public."txindex" AS smallint;
-- DROP TYPE public."vote";

CREATE TYPE public."vote" AS ENUM (
	'Yes',
	'No',
	'Abstain');

-- DROP TYPE public."voterrole";

CREATE TYPE public."voterrole" AS ENUM (
	'ConstitutionalCommittee',
	'DRep',
	'SPO');

-- DROP DOMAIN public."word128type";

CREATE DOMAIN public."word128type" AS numeric(39,0);
-- DROP DOMAIN public."word31type";

CREATE DOMAIN public."word31type" AS integer;
-- DROP DOMAIN public."word63type";

CREATE DOMAIN public."word63type" AS bigint;
-- DROP DOMAIN public."word64type";

CREATE DOMAIN public."word64type" AS numeric(20,0);
-- DROP SEQUENCE public.ada_pots_id_seq;

CREATE SEQUENCE public.ada_pots_id_seq
	INCREMENT BY 1
	MINVALUE 1
	MAXVALUE 9223372036854775807
	START 1
	CACHE 1
	NO CYCLE;
-- DROP SEQUENCE public.block_id_seq;

CREATE SEQUENCE public.block_id_seq
	INCREMENT BY 1
	MINVALUE 1
	MAXVALUE 9223372036854775807
	START 1
	CACHE 1
	NO CYCLE;
-- DROP SEQUENCE public.collateral_tx_in_id_seq;

CREATE SEQUENCE public.collateral_tx_in_id_seq
	INCREMENT BY 1
	MINVALUE 1
	MAXVALUE 9223372036854775807
	START 1
	CACHE 1
	NO CYCLE;
-- DROP SEQUENCE public.collateral_tx_out_id_seq;

CREATE SEQUENCE public.collateral_tx_out_id_seq
	INCREMENT BY 1
	MINVALUE 1
	MAXVALUE 9223372036854775807
	START 1
	CACHE 1
	NO CYCLE;
-- DROP SEQUENCE public.committee_de_registration_id_seq;

CREATE SEQUENCE public.committee_de_registration_id_seq
	INCREMENT BY 1
	MINVALUE 1
	MAXVALUE 9223372036854775807
	START 1
	CACHE 1
	NO CYCLE;
-- DROP SEQUENCE public.committee_hash_id_seq;

CREATE SEQUENCE public.committee_hash_id_seq
	INCREMENT BY 1
	MINVALUE 1
	MAXVALUE 9223372036854775807
	START 1
	CACHE 1
	NO CYCLE;
-- DROP SEQUENCE public.committee_id_seq;

CREATE SEQUENCE public.committee_id_seq
	INCREMENT BY 1
	MINVALUE 1
	MAXVALUE 9223372036854775807
	START 1
	CACHE 1
	NO CYCLE;
-- DROP SEQUENCE public.committee_member_id_seq;

CREATE SEQUENCE public.committee_member_id_seq
	INCREMENT BY 1
	MINVALUE 1
	MAXVALUE 9223372036854775807
	START 1
	CACHE 1
	NO CYCLE;
-- DROP SEQUENCE public.committee_registration_id_seq;

CREATE SEQUENCE public.committee_registration_id_seq
	INCREMENT BY 1
	MINVALUE 1
	MAXVALUE 9223372036854775807
	START 1
	CACHE 1
	NO CYCLE;
-- DROP SEQUENCE public.constitution_id_seq;

CREATE SEQUENCE public.constitution_id_seq
	INCREMENT BY 1
	MINVALUE 1
	MAXVALUE 9223372036854775807
	START 1
	CACHE 1
	NO CYCLE;
-- DROP SEQUENCE public.cost_model_id_seq;

CREATE SEQUENCE public.cost_model_id_seq
	INCREMENT BY 1
	MINVALUE 1
	MAXVALUE 9223372036854775807
	START 1
	CACHE 1
	NO CYCLE;
-- DROP SEQUENCE public.datum_id_seq;

CREATE SEQUENCE public.datum_id_seq
	INCREMENT BY 1
	MINVALUE 1
	MAXVALUE 9223372036854775807
	START 1
	CACHE 1
	NO CYCLE;
-- DROP SEQUENCE public.delegation_id_seq;

CREATE SEQUENCE public.delegation_id_seq
	INCREMENT BY 1
	MINVALUE 1
	MAXVALUE 9223372036854775807
	START 1
	CACHE 1
	NO CYCLE;
-- DROP SEQUENCE public.delegation_vote_id_seq;

CREATE SEQUENCE public.delegation_vote_id_seq
	INCREMENT BY 1
	MINVALUE 1
	MAXVALUE 9223372036854775807
	START 1
	CACHE 1
	NO CYCLE;
-- DROP SEQUENCE public.delisted_pool_id_seq;

CREATE SEQUENCE public.delisted_pool_id_seq
	INCREMENT BY 1
	MINVALUE 1
	MAXVALUE 9223372036854775807
	START 1
	CACHE 1
	NO CYCLE;
-- DROP SEQUENCE public.drep_distr_id_seq;

CREATE SEQUENCE public.drep_distr_id_seq
	INCREMENT BY 1
	MINVALUE 1
	MAXVALUE 9223372036854775807
	START 1
	CACHE 1
	NO CYCLE;
-- DROP SEQUENCE public.drep_hash_id_seq;

CREATE SEQUENCE public.drep_hash_id_seq
	INCREMENT BY 1
	MINVALUE 1
	MAXVALUE 9223372036854775807
	START 1
	CACHE 1
	NO CYCLE;
-- DROP SEQUENCE public.drep_registration_id_seq;

CREATE SEQUENCE public.drep_registration_id_seq
	INCREMENT BY 1
	MINVALUE 1
	MAXVALUE 9223372036854775807
	START 1
	CACHE 1
	NO CYCLE;
-- DROP SEQUENCE public.epoch_id_seq;

CREATE SEQUENCE public.epoch_id_seq
	INCREMENT BY 1
	MINVALUE 1
	MAXVALUE 9223372036854775807
	START 1
	CACHE 1
	NO CYCLE;
-- DROP SEQUENCE public.epoch_param_id_seq;

CREATE SEQUENCE public.epoch_param_id_seq
	INCREMENT BY 1
	MINVALUE 1
	MAXVALUE 9223372036854775807
	START 1
	CACHE 1
	NO CYCLE;
-- DROP SEQUENCE public.epoch_stake_id_seq;

CREATE SEQUENCE public.epoch_stake_id_seq
	INCREMENT BY 1
	MINVALUE 1
	MAXVALUE 9223372036854775807
	START 1
	CACHE 1
	NO CYCLE;
-- DROP SEQUENCE public.epoch_stake_progress_id_seq;

CREATE SEQUENCE public.epoch_stake_progress_id_seq
	INCREMENT BY 1
	MINVALUE 1
	MAXVALUE 9223372036854775807
	START 1
	CACHE 1
	NO CYCLE;
-- DROP SEQUENCE public.epoch_state_id_seq;

CREATE SEQUENCE public.epoch_state_id_seq
	INCREMENT BY 1
	MINVALUE 1
	MAXVALUE 9223372036854775807
	START 1
	CACHE 1
	NO CYCLE;
-- DROP SEQUENCE public.epoch_sync_time_id_seq;

CREATE SEQUENCE public.epoch_sync_time_id_seq
	INCREMENT BY 1
	MINVALUE 1
	MAXVALUE 9223372036854775807
	START 1
	CACHE 1
	NO CYCLE;
-- DROP SEQUENCE public.event_info_id_seq;

CREATE SEQUENCE public.event_info_id_seq
	INCREMENT BY 1
	MINVALUE 1
	MAXVALUE 9223372036854775807
	START 1
	CACHE 1
	NO CYCLE;
-- DROP SEQUENCE public.extra_key_witness_id_seq;

CREATE SEQUENCE public.extra_key_witness_id_seq
	INCREMENT BY 1
	MINVALUE 1
	MAXVALUE 9223372036854775807
	START 1
	CACHE 1
	NO CYCLE;
-- DROP SEQUENCE public.extra_migrations_id_seq;

CREATE SEQUENCE public.extra_migrations_id_seq
	INCREMENT BY 1
	MINVALUE 1
	MAXVALUE 9223372036854775807
	START 1
	CACHE 1
	NO CYCLE;
-- DROP SEQUENCE public.gov_action_proposal_id_seq;

CREATE SEQUENCE public.gov_action_proposal_id_seq
	INCREMENT BY 1
	MINVALUE 1
	MAXVALUE 9223372036854775807
	START 1
	CACHE 1
	NO CYCLE;
-- DROP SEQUENCE public.ma_tx_mint_id_seq;

CREATE SEQUENCE public.ma_tx_mint_id_seq
	INCREMENT BY 1
	MINVALUE 1
	MAXVALUE 9223372036854775807
	START 1
	CACHE 1
	NO CYCLE;
-- DROP SEQUENCE public.ma_tx_out_id_seq;

CREATE SEQUENCE public.ma_tx_out_id_seq
	INCREMENT BY 1
	MINVALUE 1
	MAXVALUE 9223372036854775807
	START 1
	CACHE 1
	NO CYCLE;
-- DROP SEQUENCE public.meta_id_seq;

CREATE SEQUENCE public.meta_id_seq
	INCREMENT BY 1
	MINVALUE 1
	MAXVALUE 9223372036854775807
	START 1
	CACHE 1
	NO CYCLE;
-- DROP SEQUENCE public.multi_asset_id_seq;

CREATE SEQUENCE public.multi_asset_id_seq
	INCREMENT BY 1
	MINVALUE 1
	MAXVALUE 9223372036854775807
	START 1
	CACHE 1
	NO CYCLE;
-- DROP SEQUENCE public.new_committee_id_seq;

CREATE SEQUENCE public.new_committee_id_seq
	INCREMENT BY 1
	MINVALUE 1
	MAXVALUE 9223372036854775807
	START 1
	CACHE 1
	NO CYCLE;
-- DROP SEQUENCE public.off_chain_pool_data_id_seq;

CREATE SEQUENCE public.off_chain_pool_data_id_seq
	INCREMENT BY 1
	MINVALUE 1
	MAXVALUE 9223372036854775807
	START 1
	CACHE 1
	NO CYCLE;
-- DROP SEQUENCE public.off_chain_pool_fetch_error_id_seq;

CREATE SEQUENCE public.off_chain_pool_fetch_error_id_seq
	INCREMENT BY 1
	MINVALUE 1
	MAXVALUE 9223372036854775807
	START 1
	CACHE 1
	NO CYCLE;
-- DROP SEQUENCE public.off_chain_vote_author_id_seq;

CREATE SEQUENCE public.off_chain_vote_author_id_seq
	INCREMENT BY 1
	MINVALUE 1
	MAXVALUE 9223372036854775807
	START 1
	CACHE 1
	NO CYCLE;
-- DROP SEQUENCE public.off_chain_vote_data_id_seq;

CREATE SEQUENCE public.off_chain_vote_data_id_seq
	INCREMENT BY 1
	MINVALUE 1
	MAXVALUE 9223372036854775807
	START 1
	CACHE 1
	NO CYCLE;
-- DROP SEQUENCE public.off_chain_vote_drep_data_id_seq;

CREATE SEQUENCE public.off_chain_vote_drep_data_id_seq
	INCREMENT BY 1
	MINVALUE 1
	MAXVALUE 9223372036854775807
	START 1
	CACHE 1
	NO CYCLE;
-- DROP SEQUENCE public.off_chain_vote_external_update_id_seq;

CREATE SEQUENCE public.off_chain_vote_external_update_id_seq
	INCREMENT BY 1
	MINVALUE 1
	MAXVALUE 9223372036854775807
	START 1
	CACHE 1
	NO CYCLE;
-- DROP SEQUENCE public.off_chain_vote_fetch_error_id_seq;

CREATE SEQUENCE public.off_chain_vote_fetch_error_id_seq
	INCREMENT BY 1
	MINVALUE 1
	MAXVALUE 9223372036854775807
	START 1
	CACHE 1
	NO CYCLE;
-- DROP SEQUENCE public.off_chain_vote_gov_action_data_id_seq;

CREATE SEQUENCE public.off_chain_vote_gov_action_data_id_seq
	INCREMENT BY 1
	MINVALUE 1
	MAXVALUE 9223372036854775807
	START 1
	CACHE 1
	NO CYCLE;
-- DROP SEQUENCE public.off_chain_vote_reference_id_seq;

CREATE SEQUENCE public.off_chain_vote_reference_id_seq
	INCREMENT BY 1
	MINVALUE 1
	MAXVALUE 9223372036854775807
	START 1
	CACHE 1
	NO CYCLE;
-- DROP SEQUENCE public.param_proposal_id_seq;

CREATE SEQUENCE public.param_proposal_id_seq
	INCREMENT BY 1
	MINVALUE 1
	MAXVALUE 9223372036854775807
	START 1
	CACHE 1
	NO CYCLE;
-- DROP SEQUENCE public.pool_hash_id_seq;

CREATE SEQUENCE public.pool_hash_id_seq
	INCREMENT BY 1
	MINVALUE 1
	MAXVALUE 9223372036854775807
	START 1
	CACHE 1
	NO CYCLE;
-- DROP SEQUENCE public.pool_metadata_ref_id_seq;

CREATE SEQUENCE public.pool_metadata_ref_id_seq
	INCREMENT BY 1
	MINVALUE 1
	MAXVALUE 9223372036854775807
	START 1
	CACHE 1
	NO CYCLE;
-- DROP SEQUENCE public.pool_owner_id_seq;

CREATE SEQUENCE public.pool_owner_id_seq
	INCREMENT BY 1
	MINVALUE 1
	MAXVALUE 9223372036854775807
	START 1
	CACHE 1
	NO CYCLE;
-- DROP SEQUENCE public.pool_relay_id_seq;

CREATE SEQUENCE public.pool_relay_id_seq
	INCREMENT BY 1
	MINVALUE 1
	MAXVALUE 9223372036854775807
	START 1
	CACHE 1
	NO CYCLE;
-- DROP SEQUENCE public.pool_retire_id_seq;

CREATE SEQUENCE public.pool_retire_id_seq
	INCREMENT BY 1
	MINVALUE 1
	MAXVALUE 9223372036854775807
	START 1
	CACHE 1
	NO CYCLE;
-- DROP SEQUENCE public.pool_stat_id_seq;

CREATE SEQUENCE public.pool_stat_id_seq
	INCREMENT BY 1
	MINVALUE 1
	MAXVALUE 9223372036854775807
	START 1
	CACHE 1
	NO CYCLE;
-- DROP SEQUENCE public.pool_update_id_seq;

CREATE SEQUENCE public.pool_update_id_seq
	INCREMENT BY 1
	MINVALUE 1
	MAXVALUE 9223372036854775807
	START 1
	CACHE 1
	NO CYCLE;
-- DROP SEQUENCE public.pot_transfer_id_seq;

CREATE SEQUENCE public.pot_transfer_id_seq
	INCREMENT BY 1
	MINVALUE 1
	MAXVALUE 9223372036854775807
	START 1
	CACHE 1
	NO CYCLE;
-- DROP SEQUENCE public.redeemer_data_id_seq;

CREATE SEQUENCE public.redeemer_data_id_seq
	INCREMENT BY 1
	MINVALUE 1
	MAXVALUE 9223372036854775807
	START 1
	CACHE 1
	NO CYCLE;
-- DROP SEQUENCE public.redeemer_id_seq;

CREATE SEQUENCE public.redeemer_id_seq
	INCREMENT BY 1
	MINVALUE 1
	MAXVALUE 9223372036854775807
	START 1
	CACHE 1
	NO CYCLE;
-- DROP SEQUENCE public.reference_tx_in_id_seq;

CREATE SEQUENCE public.reference_tx_in_id_seq
	INCREMENT BY 1
	MINVALUE 1
	MAXVALUE 9223372036854775807
	START 1
	CACHE 1
	NO CYCLE;
-- DROP SEQUENCE public.reserve_id_seq;

CREATE SEQUENCE public.reserve_id_seq
	INCREMENT BY 1
	MINVALUE 1
	MAXVALUE 9223372036854775807
	START 1
	CACHE 1
	NO CYCLE;
-- DROP SEQUENCE public.reserved_pool_ticker_id_seq;

CREATE SEQUENCE public.reserved_pool_ticker_id_seq
	INCREMENT BY 1
	MINVALUE 1
	MAXVALUE 9223372036854775807
	START 1
	CACHE 1
	NO CYCLE;
-- DROP SEQUENCE public.reverse_index_id_seq;

CREATE SEQUENCE public.reverse_index_id_seq
	INCREMENT BY 1
	MINVALUE 1
	MAXVALUE 9223372036854775807
	START 1
	CACHE 1
	NO CYCLE;
-- DROP SEQUENCE public.schema_version_id_seq;

CREATE SEQUENCE public.schema_version_id_seq
	INCREMENT BY 1
	MINVALUE 1
	MAXVALUE 2147483647
	START 1
	CACHE 1
	NO CYCLE;
-- DROP SEQUENCE public.script_id_seq;

CREATE SEQUENCE public.script_id_seq
	INCREMENT BY 1
	MINVALUE 1
	MAXVALUE 9223372036854775807
	START 1
	CACHE 1
	NO CYCLE;
-- DROP SEQUENCE public.slot_leader_id_seq;

CREATE SEQUENCE public.slot_leader_id_seq
	INCREMENT BY 1
	MINVALUE 1
	MAXVALUE 9223372036854775807
	START 1
	CACHE 1
	NO CYCLE;
-- DROP SEQUENCE public.stake_address_id_seq;

CREATE SEQUENCE public.stake_address_id_seq
	INCREMENT BY 1
	MINVALUE 1
	MAXVALUE 9223372036854775807
	START 1
	CACHE 1
	NO CYCLE;
-- DROP SEQUENCE public.stake_deregistration_id_seq;

CREATE SEQUENCE public.stake_deregistration_id_seq
	INCREMENT BY 1
	MINVALUE 1
	MAXVALUE 9223372036854775807
	START 1
	CACHE 1
	NO CYCLE;
-- DROP SEQUENCE public.stake_registration_id_seq;

CREATE SEQUENCE public.stake_registration_id_seq
	INCREMENT BY 1
	MINVALUE 1
	MAXVALUE 9223372036854775807
	START 1
	CACHE 1
	NO CYCLE;
-- DROP SEQUENCE public.treasury_id_seq;

CREATE SEQUENCE public.treasury_id_seq
	INCREMENT BY 1
	MINVALUE 1
	MAXVALUE 9223372036854775807
	START 1
	CACHE 1
	NO CYCLE;
-- DROP SEQUENCE public.treasury_withdrawal_id_seq;

CREATE SEQUENCE public.treasury_withdrawal_id_seq
	INCREMENT BY 1
	MINVALUE 1
	MAXVALUE 9223372036854775807
	START 1
	CACHE 1
	NO CYCLE;
-- DROP SEQUENCE public.tx_cbor_id_seq;

CREATE SEQUENCE public.tx_cbor_id_seq
	INCREMENT BY 1
	MINVALUE 1
	MAXVALUE 9223372036854775807
	START 1
	CACHE 1
	NO CYCLE;
-- DROP SEQUENCE public.tx_id_seq;

CREATE SEQUENCE public.tx_id_seq
	INCREMENT BY 1
	MINVALUE 1
	MAXVALUE 9223372036854775807
	START 1
	CACHE 1
	NO CYCLE;
-- DROP SEQUENCE public.tx_in_id_seq;

CREATE SEQUENCE public.tx_in_id_seq
	INCREMENT BY 1
	MINVALUE 1
	MAXVALUE 9223372036854775807
	START 1
	CACHE 1
	NO CYCLE;
-- DROP SEQUENCE public.tx_metadata_id_seq;

CREATE SEQUENCE public.tx_metadata_id_seq
	INCREMENT BY 1
	MINVALUE 1
	MAXVALUE 9223372036854775807
	START 1
	CACHE 1
	NO CYCLE;
-- DROP SEQUENCE public.tx_out_id_seq;

CREATE SEQUENCE public.tx_out_id_seq
	INCREMENT BY 1
	MINVALUE 1
	MAXVALUE 9223372036854775807
	START 1
	CACHE 1
	NO CYCLE;
-- DROP SEQUENCE public.voting_anchor_id_seq;

CREATE SEQUENCE public.voting_anchor_id_seq
	INCREMENT BY 1
	MINVALUE 1
	MAXVALUE 9223372036854775807
	START 1
	CACHE 1
	NO CYCLE;
-- DROP SEQUENCE public.voting_procedure_id_seq;

CREATE SEQUENCE public.voting_procedure_id_seq
	INCREMENT BY 1
	MINVALUE 1
	MAXVALUE 9223372036854775807
	START 1
	CACHE 1
	NO CYCLE;
-- DROP SEQUENCE public.withdrawal_id_seq;

CREATE SEQUENCE public.withdrawal_id_seq
	INCREMENT BY 1
	MINVALUE 1
	MAXVALUE 9223372036854775807
	START 1
	CACHE 1
	NO CYCLE;-- public.ada_pots definition

-- Drop table

-- DROP TABLE public.ada_pots;

CREATE TABLE public.ada_pots ( id bigserial NOT NULL, slot_no public."word63type" NOT NULL, epoch_no public."word31type" NOT NULL, treasury public."lovelace" NOT NULL, reserves public."lovelace" NOT NULL, rewards public."lovelace" NOT NULL, utxo public."lovelace" NOT NULL, deposits_stake public."lovelace" NOT NULL, fees public."lovelace" NOT NULL, block_id int8 NOT NULL, deposits_drep public."lovelace" NOT NULL, deposits_proposal public."lovelace" NOT NULL, CONSTRAINT ada_pots_pkey PRIMARY KEY (id));
CREATE UNIQUE INDEX unique_ada_pots ON public.ada_pots USING btree (block_id);


-- public.block definition

-- Drop table

-- DROP TABLE public.block;

CREATE TABLE public.block ( id bigserial NOT NULL, hash public.hash32type NOT NULL, epoch_no public."word31type" NULL, slot_no public."word63type" NULL, epoch_slot_no public."word31type" NULL, block_no public."word31type" NULL, previous_id int8 NULL, slot_leader_id int8 NOT NULL, "size" public."word31type" NOT NULL, "time" timestamp NOT NULL, tx_count int8 NOT NULL, proto_major public."word31type" NOT NULL, proto_minor public."word31type" NOT NULL, vrf_key varchar NULL, op_cert public.hash32type NULL, op_cert_counter public."word63type" NULL, CONSTRAINT block_pkey PRIMARY KEY (id), CONSTRAINT unique_block UNIQUE (hash));
CREATE INDEX bf_idx_block_hash_encoded ON public.block USING hash (encode((hash)::bytea, 'hex'::text));
CREATE INDEX idx_block_block_no ON public.block USING btree (block_no);
CREATE INDEX idx_block_epoch_no ON public.block USING btree (epoch_no);
CREATE INDEX idx_block_previous_id ON public.block USING btree (previous_id);
CREATE INDEX idx_block_slot_leader_id ON public.block USING btree (slot_leader_id);
CREATE INDEX idx_block_slot_no ON public.block USING btree (slot_no);
CREATE INDEX idx_block_time ON public.block USING btree ("time");


-- public.cardumen_off_chain_drep_metadata_cache definition

-- Drop table

-- DROP TABLE public.cardumen_off_chain_drep_metadata_cache;

CREATE TABLE public.cardumen_off_chain_drep_metadata_cache ( drep_id text NOT NULL, given_name text NULL, image_url text NULL, payment_address text NULL, objectives text NULL, motivations text NULL, qualifications text NULL, url text NULL, hash text NULL, fetched_at timestamp DEFAULT now() NULL, CONSTRAINT cardumen_off_chain_drep_metadata_cache_pkey PRIMARY KEY (drep_id));


-- public.collateral_tx_in definition

-- Drop table

-- DROP TABLE public.collateral_tx_in;

CREATE TABLE public.collateral_tx_in ( id bigserial NOT NULL, tx_in_id int8 NOT NULL, tx_out_id int8 NOT NULL, tx_out_index public."txindex" NOT NULL, CONSTRAINT collateral_tx_in_pkey PRIMARY KEY (id));
CREATE INDEX bf_idx_collateral_tx_in_tx_in_id ON public.collateral_tx_in USING btree (tx_in_id);
CREATE INDEX idx_collateral_tx_in_tx_out_id ON public.collateral_tx_in USING btree (tx_out_id);
CREATE UNIQUE INDEX unique_col_txin ON public.collateral_tx_in USING btree (tx_in_id, tx_out_id, tx_out_index);


-- public.collateral_tx_out definition

-- Drop table

-- DROP TABLE public.collateral_tx_out;

CREATE TABLE public.collateral_tx_out ( id bigserial NOT NULL, tx_id int8 NOT NULL, "index" public."txindex" NOT NULL, address varchar NOT NULL, address_has_script bool NOT NULL, payment_cred public.hash28type NULL, stake_address_id int8 NULL, value public."lovelace" NOT NULL, data_hash public.hash32type NULL, multi_assets_descr varchar NOT NULL, inline_datum_id int8 NULL, reference_script_id int8 NULL, CONSTRAINT collateral_tx_out_pkey PRIMARY KEY (id));
CREATE INDEX bf_idx_col_tx_out ON public.collateral_tx_out USING btree (tx_id);
CREATE INDEX collateral_tx_out_inline_datum_id_idx ON public.collateral_tx_out USING btree (inline_datum_id);
CREATE INDEX collateral_tx_out_reference_script_id_idx ON public.collateral_tx_out USING btree (reference_script_id);
CREATE INDEX collateral_tx_out_stake_address_id_idx ON public.collateral_tx_out USING btree (stake_address_id);
CREATE UNIQUE INDEX unique_col_txout ON public.collateral_tx_out USING btree (tx_id, index);


-- public.committee definition

-- Drop table

-- DROP TABLE public.committee;

CREATE TABLE public.committee ( id bigserial NOT NULL, gov_action_proposal_id int8 NULL, quorum_numerator int8 NOT NULL, quorum_denominator int8 NOT NULL, CONSTRAINT committee_pkey PRIMARY KEY (id));


-- public.committee_de_registration definition

-- Drop table

-- DROP TABLE public.committee_de_registration;

CREATE TABLE public.committee_de_registration ( id bigserial NOT NULL, tx_id int8 NOT NULL, cert_index int4 NOT NULL, voting_anchor_id int8 NULL, cold_key_id int8 NOT NULL, CONSTRAINT committee_de_registration_pkey PRIMARY KEY (id));


-- public.committee_hash definition

-- Drop table

-- DROP TABLE public.committee_hash;

CREATE TABLE public.committee_hash ( id bigserial NOT NULL, raw public.hash28type NOT NULL, has_script bool NOT NULL, CONSTRAINT committee_hash_pkey PRIMARY KEY (id), CONSTRAINT unique_committee_hash UNIQUE (raw, has_script));


-- public.committee_registration definition

-- Drop table

-- DROP TABLE public.committee_registration;

CREATE TABLE public.committee_registration ( id bigserial NOT NULL, tx_id int8 NOT NULL, cert_index int4 NOT NULL, cold_key_id int8 NOT NULL, hot_key_id int8 NOT NULL, CONSTRAINT committee_registration_pkey PRIMARY KEY (id));


-- public.constitution definition

-- Drop table

-- DROP TABLE public.constitution;

CREATE TABLE public.constitution ( id bigserial NOT NULL, gov_action_proposal_id int8 NULL, voting_anchor_id int8 NOT NULL, script_hash public.hash28type NULL, CONSTRAINT constitution_pkey PRIMARY KEY (id));


-- public.cost_model definition

-- Drop table

-- DROP TABLE public.cost_model;

CREATE TABLE public.cost_model ( id bigserial NOT NULL, costs jsonb NOT NULL, hash public.hash32type NOT NULL, CONSTRAINT cost_model_pkey PRIMARY KEY (id), CONSTRAINT unique_cost_model UNIQUE (hash));


-- public.datum definition

-- Drop table

-- DROP TABLE public.datum;

CREATE TABLE public.datum ( id bigserial NOT NULL, hash public.hash32type NOT NULL, tx_id int8 NOT NULL, value jsonb NULL, bytes bytea NOT NULL, CONSTRAINT datum_pkey PRIMARY KEY (id), CONSTRAINT unique_datum UNIQUE (hash));
CREATE INDEX bf_idx_datum_hash ON public.datum USING hash (encode((hash)::bytea, 'hex'::text));
CREATE INDEX idx_datum_tx_id ON public.datum USING btree (tx_id);


-- public.delegation definition

-- Drop table

-- DROP TABLE public.delegation;

CREATE TABLE public.delegation ( id bigserial NOT NULL, addr_id int8 NOT NULL, cert_index int4 NOT NULL, pool_hash_id int8 NOT NULL, active_epoch_no int8 NOT NULL, tx_id int8 NOT NULL, slot_no public."word63type" NOT NULL, redeemer_id int8 NULL, CONSTRAINT delegation_pkey PRIMARY KEY (id));
CREATE INDEX idx_delegation_active_epoch_no ON public.delegation USING btree (active_epoch_no);
CREATE INDEX idx_delegation_addr_id ON public.delegation USING btree (addr_id);
CREATE INDEX idx_delegation_pool_hash_id ON public.delegation USING btree (pool_hash_id);
CREATE INDEX idx_delegation_redeemer_id ON public.delegation USING btree (redeemer_id);
CREATE INDEX idx_delegation_tx_id ON public.delegation USING btree (tx_id);
CREATE UNIQUE INDEX unique_delegation ON public.delegation USING btree (tx_id, cert_index);


-- public.delegation_vote definition

-- Drop table

-- DROP TABLE public.delegation_vote;

CREATE TABLE public.delegation_vote ( id bigserial NOT NULL, addr_id int8 NOT NULL, cert_index int4 NOT NULL, drep_hash_id int8 NOT NULL, tx_id int8 NOT NULL, redeemer_id int8 NULL, CONSTRAINT delegation_vote_pkey PRIMARY KEY (id));
CREATE INDEX bf_idx_delegation_vote_addr_id ON public.delegation_vote USING hash (addr_id);


-- public.delisted_pool definition

-- Drop table

-- DROP TABLE public.delisted_pool;

CREATE TABLE public.delisted_pool ( id bigserial NOT NULL, hash_raw public.hash28type NOT NULL, CONSTRAINT delisted_pool_pkey PRIMARY KEY (id), CONSTRAINT unique_delisted_pool UNIQUE (hash_raw));


-- public.drep_distr definition

-- Drop table

-- DROP TABLE public.drep_distr;

CREATE TABLE public.drep_distr ( id bigserial NOT NULL, hash_id int8 NOT NULL, amount int8 NOT NULL, epoch_no public."word31type" NOT NULL, active_until public."word31type" NULL, CONSTRAINT drep_distr_pkey PRIMARY KEY (id), CONSTRAINT unique_drep_distr UNIQUE (hash_id, epoch_no));


-- public.drep_hash definition

-- Drop table

-- DROP TABLE public.drep_hash;

CREATE TABLE public.drep_hash ( id bigserial NOT NULL, raw public.hash28type NULL, "view" varchar NOT NULL, has_script bool NOT NULL, CONSTRAINT drep_hash_pkey PRIMARY KEY (id), CONSTRAINT unique_drep_hash UNIQUE (raw, has_script));
CREATE INDEX bf_idx_drep_hash_has_script ON public.drep_hash USING hash (has_script);
CREATE INDEX bf_idx_drep_hash_raw ON public.drep_hash USING hash (raw);
CREATE INDEX bf_idx_drep_hash_view ON public.drep_hash USING hash (view);


-- public.drep_registration definition

-- Drop table

-- DROP TABLE public.drep_registration;

CREATE TABLE public.drep_registration ( id bigserial NOT NULL, tx_id int8 NOT NULL, cert_index int4 NOT NULL, deposit int8 NULL, drep_hash_id int8 NOT NULL, voting_anchor_id int8 NULL, CONSTRAINT drep_registration_pkey PRIMARY KEY (id));
CREATE INDEX bf_idx_drep_registration_hash_deposit ON public.drep_registration USING btree (drep_hash_id, deposit, tx_id);


-- public.epoch definition

-- Drop table

-- DROP TABLE public.epoch;

CREATE TABLE public.epoch ( id bigserial NOT NULL, out_sum public."word128type" NOT NULL, fees public."lovelace" NOT NULL, tx_count public."word31type" NOT NULL, blk_count public."word31type" NOT NULL, "no" public."word31type" NOT NULL, start_time timestamp NOT NULL, end_time timestamp NOT NULL, CONSTRAINT epoch_pkey PRIMARY KEY (id), CONSTRAINT unique_epoch UNIQUE (no));
CREATE INDEX idx_epoch_no ON public.epoch USING btree (no);


-- public.epoch_param definition

-- Drop table

-- DROP TABLE public.epoch_param;

CREATE TABLE public.epoch_param ( id bigserial NOT NULL, epoch_no public."word31type" NOT NULL, min_fee_a public."word31type" NOT NULL, min_fee_b public."word31type" NOT NULL, max_block_size public."word31type" NOT NULL, max_tx_size public."word31type" NOT NULL, max_bh_size public."word31type" NOT NULL, key_deposit public."lovelace" NOT NULL, pool_deposit public."lovelace" NOT NULL, max_epoch public."word31type" NOT NULL, optimal_pool_count public."word31type" NOT NULL, influence float8 NOT NULL, monetary_expand_rate float8 NOT NULL, treasury_growth_rate float8 NOT NULL, decentralisation float8 NOT NULL, protocol_major public."word31type" NOT NULL, protocol_minor public."word31type" NOT NULL, min_utxo_value public."lovelace" NOT NULL, min_pool_cost public."lovelace" NOT NULL, nonce public.hash32type NULL, cost_model_id int8 NULL, price_mem float8 NULL, price_step float8 NULL, max_tx_ex_mem public."word64type" NULL, max_tx_ex_steps public."word64type" NULL, max_block_ex_mem public."word64type" NULL, max_block_ex_steps public."word64type" NULL, max_val_size public."word64type" NULL, collateral_percent public."word31type" NULL, max_collateral_inputs public."word31type" NULL, block_id int8 NOT NULL, extra_entropy public.hash32type NULL, coins_per_utxo_size public."lovelace" NULL, pvt_motion_no_confidence float8 NULL, pvt_committee_normal float8 NULL, pvt_committee_no_confidence float8 NULL, pvt_hard_fork_initiation float8 NULL, dvt_motion_no_confidence float8 NULL, dvt_committee_normal float8 NULL, dvt_committee_no_confidence float8 NULL, dvt_update_to_constitution float8 NULL, dvt_hard_fork_initiation float8 NULL, dvt_p_p_network_group float8 NULL, dvt_p_p_economic_group float8 NULL, dvt_p_p_technical_group float8 NULL, dvt_p_p_gov_group float8 NULL, dvt_treasury_withdrawal float8 NULL, committee_min_size public."word64type" NULL, committee_max_term_length public."word64type" NULL, gov_action_lifetime public."word64type" NULL, gov_action_deposit public."word64type" NULL, drep_deposit public."word64type" NULL, drep_activity public."word64type" NULL, pvtpp_security_group float8 NULL, min_fee_ref_script_cost_per_byte float8 NULL, CONSTRAINT epoch_param_pkey PRIMARY KEY (id));
CREATE INDEX idx_epoch_param_block_id ON public.epoch_param USING btree (block_id);
CREATE INDEX idx_epoch_param_cost_model_id ON public.epoch_param USING btree (cost_model_id);
CREATE UNIQUE INDEX unique_epoch_param ON public.epoch_param USING btree (epoch_no, block_id);


-- public.epoch_stake definition

-- Drop table

-- DROP TABLE public.epoch_stake;

CREATE TABLE public.epoch_stake ( id bigserial NOT NULL, addr_id int8 NOT NULL, pool_id int8 NOT NULL, amount public."lovelace" NOT NULL, epoch_no public."word31type" NOT NULL, CONSTRAINT epoch_stake_pkey PRIMARY KEY (id), CONSTRAINT unique_epoch_stake UNIQUE (epoch_no, addr_id, pool_id));
CREATE UNIQUE INDEX bf_u_idx_epoch_stake_epoch_and_id ON public.epoch_stake USING btree (epoch_no, id);
CREATE INDEX idx_epoch_stake_addr_id ON public.epoch_stake USING btree (addr_id);
CREATE INDEX idx_epoch_stake_epoch_no ON public.epoch_stake USING btree (epoch_no);
CREATE INDEX idx_epoch_stake_pool_id ON public.epoch_stake USING btree (pool_id);
CREATE UNIQUE INDEX unique_stake ON public.epoch_stake USING btree (epoch_no, addr_id, pool_id);


-- public.epoch_stake_progress definition

-- Drop table

-- DROP TABLE public.epoch_stake_progress;

CREATE TABLE public.epoch_stake_progress ( id bigserial NOT NULL, epoch_no public."word31type" NOT NULL, completed bool NOT NULL, CONSTRAINT epoch_stake_progress_pkey PRIMARY KEY (id), CONSTRAINT unique_epoch_stake_progress UNIQUE (epoch_no));


-- public.epoch_state definition

-- Drop table

-- DROP TABLE public.epoch_state;

CREATE TABLE public.epoch_state ( id bigserial NOT NULL, committee_id int8 NULL, no_confidence_id int8 NULL, constitution_id int8 NULL, epoch_no public."word31type" NOT NULL, CONSTRAINT epoch_state_pkey PRIMARY KEY (id));


-- public.epoch_sync_time definition

-- Drop table

-- DROP TABLE public.epoch_sync_time;

CREATE TABLE public.epoch_sync_time ( id bigserial NOT NULL, "no" int8 NOT NULL, seconds public."word63type" NOT NULL, state public."syncstatetype" NOT NULL, CONSTRAINT epoch_sync_time_pkey PRIMARY KEY (id), CONSTRAINT unique_epoch_sync_time UNIQUE (no));


-- public.event_info definition

-- Drop table

-- DROP TABLE public.event_info;

CREATE TABLE public.event_info ( id bigserial NOT NULL, tx_id int8 NULL, epoch public."word31type" NOT NULL, "type" varchar NOT NULL, explanation varchar NULL, CONSTRAINT event_info_pkey PRIMARY KEY (id));


-- public.extra_key_witness definition

-- Drop table

-- DROP TABLE public.extra_key_witness;

CREATE TABLE public.extra_key_witness ( id bigserial NOT NULL, hash public.hash28type NOT NULL, tx_id int8 NOT NULL, CONSTRAINT extra_key_witness_pkey PRIMARY KEY (id));
CREATE INDEX idx_extra_key_witness_tx_id ON public.extra_key_witness USING btree (tx_id);


-- public.extra_migrations definition

-- Drop table

-- DROP TABLE public.extra_migrations;

CREATE TABLE public.extra_migrations ( id bigserial NOT NULL, "token" varchar NOT NULL, description varchar NULL, CONSTRAINT extra_migrations_pkey PRIMARY KEY (id));


-- public.gov_action_proposal definition

-- Drop table

-- DROP TABLE public.gov_action_proposal;

CREATE TABLE public.gov_action_proposal ( id bigserial NOT NULL, tx_id int8 NOT NULL, "index" int8 NOT NULL, prev_gov_action_proposal int8 NULL, deposit public."lovelace" NOT NULL, return_address int8 NOT NULL, expiration public."word31type" NULL, voting_anchor_id int8 NULL, "type" public."govactiontype" NOT NULL, description jsonb NOT NULL, param_proposal int8 NULL, ratified_epoch public."word31type" NULL, enacted_epoch public."word31type" NULL, dropped_epoch public."word31type" NULL, expired_epoch public."word31type" NULL, CONSTRAINT gov_action_proposal_pkey PRIMARY KEY (id));


-- public.ma_tx_mint definition

-- Drop table

-- DROP TABLE public.ma_tx_mint;

CREATE TABLE public.ma_tx_mint ( id bigserial NOT NULL, quantity public."int65type" NOT NULL, tx_id int8 NOT NULL, ident int8 NOT NULL, CONSTRAINT ma_tx_mint_pkey PRIMARY KEY (id));
CREATE INDEX bf_idx_ma_tx_mint_ident ON public.ma_tx_mint USING btree (ident);
CREATE INDEX idx_ma_tx_mint_tx_id ON public.ma_tx_mint USING btree (tx_id);
CREATE UNIQUE INDEX unique_ma_tx_mint ON public.ma_tx_mint USING btree (ident, tx_id);


-- public.ma_tx_out definition

-- Drop table

-- DROP TABLE public.ma_tx_out;

CREATE TABLE public.ma_tx_out ( id bigserial NOT NULL, quantity public."word64type" NOT NULL, tx_out_id int8 NOT NULL, ident int8 NOT NULL, CONSTRAINT ma_tx_out_pkey PRIMARY KEY (id));
CREATE INDEX bf_idx_ma_tx_out_ident ON public.ma_tx_out USING btree (ident);
CREATE INDEX idx_ident ON public.ma_tx_out USING btree (ident);
CREATE INDEX idx_ma_tx_out_tx_out_id ON public.ma_tx_out USING btree (tx_out_id);
CREATE INDEX ma_tx_out_ident_index ON public.ma_tx_out USING btree (ident DESC);
CREATE UNIQUE INDEX unique_ma_tx_out ON public.ma_tx_out USING btree (ident, tx_out_id);


-- public.meta definition

-- Drop table

-- DROP TABLE public.meta;

CREATE TABLE public.meta ( id bigserial NOT NULL, start_time timestamp NOT NULL, network_name varchar NOT NULL, "version" varchar NOT NULL, CONSTRAINT meta_pkey PRIMARY KEY (id), CONSTRAINT unique_meta UNIQUE (start_time));


-- public.multi_asset definition

-- Drop table

-- DROP TABLE public.multi_asset;

CREATE TABLE public.multi_asset ( id bigserial NOT NULL, "policy" public.hash28type NOT NULL, "name" public.asset32type NOT NULL, fingerprint varchar NOT NULL, CONSTRAINT multi_asset_pkey PRIMARY KEY (id), CONSTRAINT unique_multi_asset UNIQUE (policy, name));
CREATE INDEX bf_idx_multi_asset_policy ON public.multi_asset USING hash (encode((policy)::bytea, 'hex'::text));
CREATE INDEX bf_idx_multi_asset_policy_name ON public.multi_asset USING hash (((encode((policy)::bytea, 'hex'::text) || encode((name)::bytea, 'hex'::text))));
CREATE INDEX idx_asset_id ON public.multi_asset USING btree ((((policy)::bytea || (name)::bytea)));
CREATE INDEX multi_asset_fingerprint ON public.multi_asset USING btree (fingerprint);


-- public.new_committee definition

-- Drop table

-- DROP TABLE public.new_committee;

CREATE TABLE public.new_committee ( id bigserial NOT NULL, gov_action_proposal_id int8 NOT NULL, deleted_members varchar NOT NULL, added_members varchar NOT NULL, quorum_numerator int8 NOT NULL, quorum_denominator int8 NOT NULL, CONSTRAINT new_committee_pkey PRIMARY KEY (id));


-- public.off_chain_pool_data definition

-- Drop table

-- DROP TABLE public.off_chain_pool_data;

CREATE TABLE public.off_chain_pool_data ( id bigserial NOT NULL, pool_id int8 NOT NULL, ticker_name varchar NOT NULL, hash public.hash32type NOT NULL, "json" jsonb NOT NULL, bytes bytea NOT NULL, pmr_id int8 NOT NULL, CONSTRAINT off_chain_pool_data_pkey PRIMARY KEY (id), CONSTRAINT unique_off_chain_pool_data UNIQUE (pool_id, pmr_id));
CREATE INDEX idx_off_chain_pool_data_pmr_id ON public.off_chain_pool_data USING btree (pmr_id);


-- public.off_chain_pool_fetch_error definition

-- Drop table

-- DROP TABLE public.off_chain_pool_fetch_error;

CREATE TABLE public.off_chain_pool_fetch_error ( id bigserial NOT NULL, pool_id int8 NOT NULL, fetch_time timestamp NOT NULL, pmr_id int8 NOT NULL, fetch_error varchar NOT NULL, retry_count public."word31type" NOT NULL, CONSTRAINT off_chain_pool_fetch_error_pkey PRIMARY KEY (id), CONSTRAINT unique_off_chain_pool_fetch_error UNIQUE (pool_id, fetch_time, retry_count));
CREATE INDEX idx_off_chain_pool_fetch_error_pmr_id ON public.off_chain_pool_fetch_error USING btree (pmr_id);


-- public.off_chain_vote_author definition

-- Drop table

-- DROP TABLE public.off_chain_vote_author;

CREATE TABLE public.off_chain_vote_author ( id bigserial NOT NULL, off_chain_vote_data_id int8 NOT NULL, "name" varchar NULL, witness_algorithm varchar NOT NULL, public_key varchar NOT NULL, signature varchar NOT NULL, warning varchar NULL, CONSTRAINT off_chain_vote_author_pkey PRIMARY KEY (id));


-- public.off_chain_vote_data definition

-- Drop table

-- DROP TABLE public.off_chain_vote_data;

CREATE TABLE public.off_chain_vote_data ( id bigserial NOT NULL, voting_anchor_id int8 NOT NULL, hash bytea NOT NULL, "json" jsonb NOT NULL, bytes bytea NOT NULL, warning varchar NULL, "language" varchar NOT NULL, "comment" varchar NULL, is_valid bool NULL, CONSTRAINT off_chain_vote_data_pkey PRIMARY KEY (id), CONSTRAINT unique_off_chain_vote_data UNIQUE (voting_anchor_id, hash));


-- public.off_chain_vote_drep_data definition

-- Drop table

-- DROP TABLE public.off_chain_vote_drep_data;

CREATE TABLE public.off_chain_vote_drep_data ( id bigserial NOT NULL, off_chain_vote_data_id int8 NOT NULL, payment_address varchar NULL, given_name varchar NOT NULL, objectives varchar NULL, motivations varchar NULL, qualifications varchar NULL, image_url varchar NULL, image_hash varchar NULL, CONSTRAINT off_chain_vote_drep_data_pkey PRIMARY KEY (id));


-- public.off_chain_vote_external_update definition

-- Drop table

-- DROP TABLE public.off_chain_vote_external_update;

CREATE TABLE public.off_chain_vote_external_update ( id bigserial NOT NULL, off_chain_vote_data_id int8 NOT NULL, title varchar NOT NULL, uri varchar NOT NULL, CONSTRAINT off_chain_vote_external_update_pkey PRIMARY KEY (id));


-- public.off_chain_vote_fetch_error definition

-- Drop table

-- DROP TABLE public.off_chain_vote_fetch_error;

CREATE TABLE public.off_chain_vote_fetch_error ( id bigserial NOT NULL, voting_anchor_id int8 NOT NULL, fetch_error varchar NOT NULL, fetch_time timestamp NOT NULL, retry_count public."word31type" NOT NULL, CONSTRAINT off_chain_vote_fetch_error_pkey PRIMARY KEY (id), CONSTRAINT unique_off_chain_vote_fetch_error UNIQUE (voting_anchor_id, retry_count));


-- public.off_chain_vote_gov_action_data definition

-- Drop table

-- DROP TABLE public.off_chain_vote_gov_action_data;

CREATE TABLE public.off_chain_vote_gov_action_data ( id bigserial NOT NULL, off_chain_vote_data_id int8 NOT NULL, title varchar NOT NULL, abstract varchar NOT NULL, motivation varchar NOT NULL, rationale varchar NOT NULL, CONSTRAINT off_chain_vote_gov_action_data_pkey PRIMARY KEY (id));


-- public.off_chain_vote_reference definition

-- Drop table

-- DROP TABLE public.off_chain_vote_reference;

CREATE TABLE public.off_chain_vote_reference ( id bigserial NOT NULL, off_chain_vote_data_id int8 NOT NULL, "label" varchar NOT NULL, uri varchar NOT NULL, hash_digest varchar NULL, hash_algorithm varchar NULL, CONSTRAINT off_chain_vote_reference_pkey PRIMARY KEY (id));


-- public.param_proposal definition

-- Drop table

-- DROP TABLE public.param_proposal;

CREATE TABLE public.param_proposal ( id bigserial NOT NULL, epoch_no public."word31type" NULL, "key" public.hash28type NULL, min_fee_a public."word64type" NULL, min_fee_b public."word64type" NULL, max_block_size public."word64type" NULL, max_tx_size public."word64type" NULL, max_bh_size public."word64type" NULL, key_deposit public."lovelace" NULL, pool_deposit public."lovelace" NULL, max_epoch public."word64type" NULL, optimal_pool_count public."word64type" NULL, influence float8 NULL, monetary_expand_rate float8 NULL, treasury_growth_rate float8 NULL, decentralisation float8 NULL, entropy public.hash32type NULL, protocol_major public."word31type" NULL, protocol_minor public."word31type" NULL, min_utxo_value public."lovelace" NULL, min_pool_cost public."lovelace" NULL, cost_model_id int8 NULL, price_mem float8 NULL, price_step float8 NULL, max_tx_ex_mem public."word64type" NULL, max_tx_ex_steps public."word64type" NULL, max_block_ex_mem public."word64type" NULL, max_block_ex_steps public."word64type" NULL, max_val_size public."word64type" NULL, collateral_percent public."word31type" NULL, max_collateral_inputs public."word31type" NULL, registered_tx_id int8 NOT NULL, coins_per_utxo_size public."lovelace" NULL, pvt_motion_no_confidence float8 NULL, pvt_committee_normal float8 NULL, pvt_committee_no_confidence float8 NULL, pvt_hard_fork_initiation float8 NULL, dvt_motion_no_confidence float8 NULL, dvt_committee_normal float8 NULL, dvt_committee_no_confidence float8 NULL, dvt_update_to_constitution float8 NULL, dvt_hard_fork_initiation float8 NULL, dvt_p_p_network_group float8 NULL, dvt_p_p_economic_group float8 NULL, dvt_p_p_technical_group float8 NULL, dvt_p_p_gov_group float8 NULL, dvt_treasury_withdrawal float8 NULL, committee_min_size public."word64type" NULL, committee_max_term_length public."word64type" NULL, gov_action_lifetime public."word64type" NULL, gov_action_deposit public."word64type" NULL, drep_deposit public."word64type" NULL, drep_activity public."word64type" NULL, pvtpp_security_group float8 NULL, min_fee_ref_script_cost_per_byte float8 NULL, CONSTRAINT param_proposal_pkey PRIMARY KEY (id));
CREATE INDEX idx_param_proposal_cost_model_id ON public.param_proposal USING btree (cost_model_id);
CREATE INDEX idx_param_proposal_registered_tx_id ON public.param_proposal USING btree (registered_tx_id);
CREATE UNIQUE INDEX unique_param_proposal ON public.param_proposal USING btree (key, registered_tx_id);


-- public.pool_hash definition

-- Drop table

-- DROP TABLE public.pool_hash;

CREATE TABLE public.pool_hash ( id bigserial NOT NULL, hash_raw public.hash28type NOT NULL, "view" varchar NOT NULL, CONSTRAINT pool_hash_pkey PRIMARY KEY (id), CONSTRAINT unique_pool_hash UNIQUE (hash_raw));
CREATE INDEX bf_idx_pool_hash_view ON public.pool_hash USING hash (view);


-- public.pool_metadata_ref definition

-- Drop table

-- DROP TABLE public.pool_metadata_ref;

CREATE TABLE public.pool_metadata_ref ( id bigserial NOT NULL, pool_id int8 NOT NULL, url varchar NOT NULL, hash public.hash32type NOT NULL, registered_tx_id int8 NOT NULL, CONSTRAINT pool_metadata_ref_pkey PRIMARY KEY (id));
CREATE INDEX idx_pool_metadata_ref_pool_id ON public.pool_metadata_ref USING btree (pool_id);
CREATE INDEX idx_pool_metadata_ref_registered_tx_id ON public.pool_metadata_ref USING btree (registered_tx_id);


-- public.pool_owner definition

-- Drop table

-- DROP TABLE public.pool_owner;

CREATE TABLE public.pool_owner ( id bigserial NOT NULL, addr_id int8 NOT NULL, pool_update_id int8 NOT NULL, CONSTRAINT pool_owner_pkey PRIMARY KEY (id));
CREATE INDEX pool_owner_pool_update_id_idx ON public.pool_owner USING btree (pool_update_id);
CREATE UNIQUE INDEX unique_pool_owner ON public.pool_owner USING btree (addr_id, pool_update_id);


-- public.pool_relay definition

-- Drop table

-- DROP TABLE public.pool_relay;

CREATE TABLE public.pool_relay ( id bigserial NOT NULL, update_id int8 NOT NULL, ipv4 varchar NULL, ipv6 varchar NULL, dns_name varchar NULL, dns_srv_name varchar NULL, port int4 NULL, CONSTRAINT pool_relay_pkey PRIMARY KEY (id));
CREATE INDEX idx_pool_relay_update_id ON public.pool_relay USING btree (update_id);
CREATE UNIQUE INDEX unique_pool_relay ON public.pool_relay USING btree (update_id, ipv4, ipv6, dns_name);


-- public.pool_retire definition

-- Drop table

-- DROP TABLE public.pool_retire;

CREATE TABLE public.pool_retire ( id bigserial NOT NULL, hash_id int8 NOT NULL, cert_index int4 NOT NULL, announced_tx_id int8 NOT NULL, retiring_epoch public."word31type" NOT NULL, CONSTRAINT pool_retire_pkey PRIMARY KEY (id));
CREATE INDEX idx_pool_retire_announced_tx_id ON public.pool_retire USING btree (announced_tx_id);
CREATE INDEX idx_pool_retire_hash_id ON public.pool_retire USING btree (hash_id);
CREATE UNIQUE INDEX unique_pool_retiring ON public.pool_retire USING btree (announced_tx_id, cert_index);


-- public.pool_stat definition

-- Drop table

-- DROP TABLE public.pool_stat;

CREATE TABLE public.pool_stat ( id bigserial NOT NULL, pool_hash_id int8 NOT NULL, epoch_no public."word31type" NOT NULL, number_of_blocks public."word64type" NOT NULL, number_of_delegators public."word64type" NOT NULL, stake public."word64type" NOT NULL, voting_power public."word64type" NULL, CONSTRAINT pool_stat_pkey PRIMARY KEY (id));


-- public.pool_update definition

-- Drop table

-- DROP TABLE public.pool_update;

CREATE TABLE public.pool_update ( id bigserial NOT NULL, hash_id int8 NOT NULL, cert_index int4 NOT NULL, vrf_key_hash public.hash32type NOT NULL, pledge public."lovelace" NOT NULL, active_epoch_no int8 NOT NULL, meta_id int8 NULL, margin float8 NOT NULL, fixed_cost public."lovelace" NOT NULL, registered_tx_id int8 NOT NULL, reward_addr_id int8 NOT NULL, deposit public."lovelace" NULL, CONSTRAINT pool_update_pkey PRIMARY KEY (id));
CREATE INDEX idx_pool_update_active_epoch_no ON public.pool_update USING btree (active_epoch_no);
CREATE INDEX idx_pool_update_hash_id ON public.pool_update USING btree (hash_id);
CREATE INDEX idx_pool_update_meta_id ON public.pool_update USING btree (meta_id);
CREATE INDEX idx_pool_update_registered_tx_id ON public.pool_update USING btree (registered_tx_id);
CREATE INDEX idx_pool_update_reward_addr ON public.pool_update USING btree (reward_addr_id);
CREATE UNIQUE INDEX unique_pool_update ON public.pool_update USING btree (registered_tx_id, cert_index);


-- public.pot_transfer definition

-- Drop table

-- DROP TABLE public.pot_transfer;

CREATE TABLE public.pot_transfer ( id bigserial NOT NULL, cert_index int4 NOT NULL, treasury public."int65type" NOT NULL, reserves public."int65type" NOT NULL, tx_id int8 NOT NULL, CONSTRAINT pot_transfer_pkey PRIMARY KEY (id));
CREATE UNIQUE INDEX unique_pot_transfer ON public.pot_transfer USING btree (tx_id, cert_index);


-- public.redeemer definition

-- Drop table

-- DROP TABLE public.redeemer;

CREATE TABLE public.redeemer ( id bigserial NOT NULL, tx_id int8 NOT NULL, unit_mem public."word63type" NOT NULL, unit_steps public."word63type" NOT NULL, fee public."lovelace" NULL, purpose public."scriptpurposetype" NOT NULL, "index" public."word31type" NOT NULL, script_hash public.hash28type NULL, redeemer_data_id int8 NOT NULL, CONSTRAINT redeemer_pkey PRIMARY KEY (id));
CREATE INDEX bf_idx_redeemer_script_hash ON public.redeemer USING hash (encode((script_hash)::bytea, 'hex'::text));
CREATE INDEX bf_idx_redeemer_tx_id ON public.redeemer USING btree (tx_id);
CREATE INDEX redeemer_redeemer_data_id_idx ON public.redeemer USING btree (redeemer_data_id);
CREATE UNIQUE INDEX unique_redeemer ON public.redeemer USING btree (tx_id, purpose, index);


-- public.redeemer_data definition

-- Drop table

-- DROP TABLE public.redeemer_data;

CREATE TABLE public.redeemer_data ( id bigserial NOT NULL, hash public.hash32type NOT NULL, tx_id int8 NOT NULL, value jsonb NULL, bytes bytea NOT NULL, CONSTRAINT redeemer_data_pkey PRIMARY KEY (id), CONSTRAINT unique_redeemer_data UNIQUE (hash));
CREATE INDEX bf_idx_redeemer_data_hash ON public.redeemer_data USING hash (encode((hash)::bytea, 'hex'::text));
CREATE INDEX redeemer_data_tx_id_idx ON public.redeemer_data USING btree (tx_id);


-- public.reference_tx_in definition

-- Drop table

-- DROP TABLE public.reference_tx_in;

CREATE TABLE public.reference_tx_in ( id bigserial NOT NULL, tx_in_id int8 NOT NULL, tx_out_id int8 NOT NULL, tx_out_index public."txindex" NOT NULL, CONSTRAINT reference_tx_in_pkey PRIMARY KEY (id));
CREATE INDEX bf_idx_reference_tx_in_tx_in_id ON public.reference_tx_in USING btree (tx_in_id);
CREATE INDEX reference_tx_in_tx_out_id_idx ON public.reference_tx_in USING btree (tx_out_id);
CREATE UNIQUE INDEX unique_ref_txin ON public.reference_tx_in USING btree (tx_in_id, tx_out_id, tx_out_index);


-- public.reserve definition

-- Drop table

-- DROP TABLE public.reserve;

CREATE TABLE public.reserve ( id bigserial NOT NULL, addr_id int8 NOT NULL, cert_index int4 NOT NULL, amount public."int65type" NOT NULL, tx_id int8 NOT NULL, CONSTRAINT reserve_pkey PRIMARY KEY (id));
CREATE INDEX idx_reserve_addr_id ON public.reserve USING btree (addr_id);
CREATE INDEX idx_reserve_tx_id ON public.reserve USING btree (tx_id);
CREATE UNIQUE INDEX unique_reserves ON public.reserve USING btree (addr_id, tx_id, cert_index);


-- public.reserved_pool_ticker definition

-- Drop table

-- DROP TABLE public.reserved_pool_ticker;

CREATE TABLE public.reserved_pool_ticker ( id bigserial NOT NULL, "name" varchar NOT NULL, pool_hash public.hash28type NOT NULL, CONSTRAINT reserved_pool_ticker_pkey PRIMARY KEY (id), CONSTRAINT unique_reserved_pool_ticker UNIQUE (name));
CREATE INDEX idx_reserved_pool_ticker_pool_hash ON public.reserved_pool_ticker USING btree (pool_hash);


-- public.reverse_index definition

-- Drop table

-- DROP TABLE public.reverse_index;

CREATE TABLE public.reverse_index ( id bigserial NOT NULL, block_id int8 NOT NULL, min_ids varchar NOT NULL, CONSTRAINT reverse_index_pkey PRIMARY KEY (id));


-- public.reward definition

-- Drop table

-- DROP TABLE public.reward;

CREATE TABLE public.reward ( addr_id int8 NOT NULL, "type" public."rewardtype" NOT NULL, amount public."lovelace" NOT NULL, spendable_epoch int8 NOT NULL, pool_id int8 NOT NULL, earned_epoch int8 GENERATED ALWAYS AS (
CASE
    WHEN type = 'refund'::rewardtype THEN spendable_epoch
    ELSE
    CASE
        WHEN spendable_epoch >= 2 THEN spendable_epoch - 2
        ELSE 0::bigint
    END
END) STORED NOT NULL, CONSTRAINT unique_reward UNIQUE (addr_id, type, earned_epoch, pool_id));
CREATE INDEX idx_reward_addr_id ON public.reward USING btree (addr_id);
CREATE INDEX idx_reward_earned_epoch ON public.reward USING btree (earned_epoch);
CREATE INDEX idx_reward_pool_id ON public.reward USING btree (pool_id);
CREATE INDEX idx_reward_spendable_epoch ON public.reward USING btree (spendable_epoch);


-- public.reward_rest definition

-- Drop table

-- DROP TABLE public.reward_rest;

CREATE TABLE public.reward_rest ( addr_id int8 NOT NULL, "type" public."rewardtype" NOT NULL, amount public."lovelace" NOT NULL, spendable_epoch int8 NOT NULL, earned_epoch int8 GENERATED ALWAYS AS (
CASE
    WHEN spendable_epoch >= 1 THEN spendable_epoch - 1
    ELSE 0::bigint
END) STORED NOT NULL);
CREATE INDEX bf_idx_reward_rest_addr_id ON public.reward_rest USING btree (addr_id);
CREATE INDEX bf_idx_reward_rest_spendable_epoch ON public.reward_rest USING btree (spendable_epoch);


-- public.schema_version definition

-- Drop table

-- DROP TABLE public.schema_version;

CREATE TABLE public.schema_version ( id bigserial NOT NULL, stage_one int8 NOT NULL, stage_two int8 NOT NULL, stage_three int8 NOT NULL, CONSTRAINT schema_version_pkey PRIMARY KEY (id));


-- public.script definition

-- Drop table

-- DROP TABLE public.script;

CREATE TABLE public.script ( id bigserial NOT NULL, tx_id int8 NOT NULL, hash public.hash28type NOT NULL, "type" public."scripttype" NOT NULL, "json" jsonb NULL, bytes bytea NULL, serialised_size public."word31type" NULL, CONSTRAINT script_pkey PRIMARY KEY (id), CONSTRAINT unique_script UNIQUE (hash));
CREATE INDEX bf_idx_scripts_hash ON public.script USING hash (encode((hash)::bytea, 'hex'::text));
CREATE INDEX idx_script_tx_id ON public.script USING btree (tx_id);


-- public.slot_leader definition

-- Drop table

-- DROP TABLE public.slot_leader;

CREATE TABLE public.slot_leader ( id bigserial NOT NULL, hash public.hash28type NOT NULL, pool_hash_id int8 NULL, description varchar NOT NULL, CONSTRAINT slot_leader_pkey PRIMARY KEY (id), CONSTRAINT unique_slot_leader UNIQUE (hash));
CREATE INDEX idx_slot_leader_pool_hash_id ON public.slot_leader USING btree (pool_hash_id);


-- public.stake_address definition

-- Drop table

-- DROP TABLE public.stake_address;

CREATE TABLE public.stake_address ( id bigserial NOT NULL, hash_raw public.addr29type NOT NULL, "view" varchar NOT NULL, script_hash public.hash28type NULL, CONSTRAINT stake_address_pkey PRIMARY KEY (id), CONSTRAINT unique_stake_address UNIQUE (hash_raw));
CREATE INDEX idx_stake_address_hash_raw ON public.stake_address USING btree (hash_raw);
CREATE INDEX idx_stake_address_view ON public.stake_address USING hash (view);
CREATE INDEX stake_address_idx ON public.stake_address USING btree (view);


-- public.stake_deregistration definition

-- Drop table

-- DROP TABLE public.stake_deregistration;

CREATE TABLE public.stake_deregistration ( id bigserial NOT NULL, addr_id int8 NOT NULL, cert_index int4 NOT NULL, epoch_no public."word31type" NOT NULL, tx_id int8 NOT NULL, redeemer_id int8 NULL, CONSTRAINT stake_deregistration_pkey PRIMARY KEY (id));
CREATE INDEX idx_stake_deregistration_addr_id ON public.stake_deregistration USING btree (addr_id);
CREATE INDEX idx_stake_deregistration_redeemer_id ON public.stake_deregistration USING btree (redeemer_id);
CREATE INDEX idx_stake_deregistration_tx_id ON public.stake_deregistration USING btree (tx_id);
CREATE UNIQUE INDEX unique_stake_deregistration ON public.stake_deregistration USING btree (tx_id, cert_index);


-- public.stake_registration definition

-- Drop table

-- DROP TABLE public.stake_registration;

CREATE TABLE public.stake_registration ( id bigserial NOT NULL, addr_id int8 NOT NULL, cert_index int4 NOT NULL, epoch_no public."word31type" NOT NULL, tx_id int8 NOT NULL, deposit public."lovelace" NULL, CONSTRAINT stake_registration_pkey PRIMARY KEY (id));
CREATE INDEX idx_stake_registration_addr_id ON public.stake_registration USING btree (addr_id);
CREATE INDEX idx_stake_registration_tx_id ON public.stake_registration USING btree (tx_id);
CREATE UNIQUE INDEX unique_stake_registration ON public.stake_registration USING btree (tx_id, cert_index);


-- public.treasury definition

-- Drop table

-- DROP TABLE public.treasury;

CREATE TABLE public.treasury ( id bigserial NOT NULL, addr_id int8 NOT NULL, cert_index int4 NOT NULL, amount public."int65type" NOT NULL, tx_id int8 NOT NULL, CONSTRAINT treasury_pkey PRIMARY KEY (id));
CREATE INDEX idx_treasury_addr_id ON public.treasury USING btree (addr_id);
CREATE INDEX idx_treasury_tx_id ON public.treasury USING btree (tx_id);
CREATE UNIQUE INDEX unique_treasury ON public.treasury USING btree (addr_id, tx_id, cert_index);


-- public.treasury_withdrawal definition

-- Drop table

-- DROP TABLE public.treasury_withdrawal;

CREATE TABLE public.treasury_withdrawal ( id bigserial NOT NULL, gov_action_proposal_id int8 NOT NULL, stake_address_id int8 NOT NULL, amount public."lovelace" NOT NULL, CONSTRAINT treasury_withdrawal_pkey PRIMARY KEY (id));


-- public.tx definition

-- Drop table

-- DROP TABLE public.tx;

CREATE TABLE public.tx ( id bigserial NOT NULL, hash public.hash32type NOT NULL, block_id int8 NOT NULL, block_index public."word31type" NOT NULL, out_sum public."lovelace" NOT NULL, fee public."lovelace" NOT NULL, deposit int8 NULL, "size" public."word31type" NOT NULL, invalid_before public."word64type" NULL, invalid_hereafter public."word64type" NULL, valid_contract bool NOT NULL, script_size public."word31type" NOT NULL, treasury_donation public."lovelace" DEFAULT 0 NOT NULL, CONSTRAINT tx_pkey PRIMARY KEY (id), CONSTRAINT unique_tx UNIQUE (hash));
CREATE INDEX bf_idx_tx_hash ON public.tx USING hash (encode((hash)::bytea, 'hex'::text));
CREATE INDEX idx_tx_block_id ON public.tx USING btree (block_id);
CREATE INDEX idx_tx_valid_contract ON public.tx USING btree (valid_contract);


-- public.tx_cbor definition

-- Drop table

-- DROP TABLE public.tx_cbor;

CREATE TABLE public.tx_cbor ( id bigserial NOT NULL, tx_id int8 NOT NULL, bytes bytea NOT NULL, CONSTRAINT tx_cbor_pkey PRIMARY KEY (id));
CREATE INDEX idx_tx_cbor_tx_id ON public.tx_cbor USING btree (tx_id);


-- public.tx_in definition

-- Drop table

-- DROP TABLE public.tx_in;

CREATE TABLE public.tx_in ( id bigserial NOT NULL, tx_in_id int8 NOT NULL, tx_out_id int8 NOT NULL, tx_out_index public."txindex" NOT NULL, redeemer_id int8 NULL, CONSTRAINT tx_in_pkey PRIMARY KEY (id));
CREATE INDEX idx_tx_in_redeemer_id ON public.tx_in USING btree (redeemer_id);
CREATE INDEX idx_tx_in_source_tx ON public.tx_in USING btree (tx_in_id);
CREATE INDEX idx_tx_in_tx_in_id ON public.tx_in USING btree (tx_in_id);
CREATE INDEX idx_tx_in_tx_out_id ON public.tx_in USING btree (tx_out_id);
CREATE UNIQUE INDEX unique_txin ON public.tx_in USING btree (tx_out_id, tx_out_index);


-- public.tx_metadata definition

-- Drop table

-- DROP TABLE public.tx_metadata;

CREATE TABLE public.tx_metadata ( id bigserial NOT NULL, "key" public."word64type" NOT NULL, "json" jsonb NULL, bytes bytea NOT NULL, tx_id int8 NOT NULL, CONSTRAINT tx_metadata_pkey PRIMARY KEY (id));
CREATE INDEX idx_tx_metadata_collection_offers ON public.tx_metadata USING btree ("substring"((json)::text, 2, 56) text_pattern_ops);
CREATE INDEX idx_tx_metadata_json_prefix ON public.tx_metadata USING btree ("substring"((json)::text, 2, 38) text_pattern_ops);
CREATE INDEX idx_tx_metadata_tx_id ON public.tx_metadata USING btree (tx_id);
CREATE UNIQUE INDEX unique_tx_metadata ON public.tx_metadata USING btree (key, tx_id);


-- public.tx_out definition

-- Drop table

-- DROP TABLE public.tx_out;

CREATE TABLE public.tx_out ( id bigserial NOT NULL, tx_id int8 NOT NULL, "index" public."txindex" NOT NULL, address varchar NOT NULL, address_has_script bool NOT NULL, payment_cred public.hash28type NULL, stake_address_id int8 NULL, value public."lovelace" NOT NULL, data_hash public.hash32type NULL, inline_datum_id int8 NULL, reference_script_id int8 NULL, consumed_by_tx_id int8 NULL, CONSTRAINT tx_out_pkey PRIMARY KEY (id), CONSTRAINT unique_txout UNIQUE (tx_id, index));
CREATE INDEX idx_tx_out_address ON public.tx_out USING hash (address);
CREATE INDEX idx_tx_out_payment_cred ON public.tx_out USING btree (payment_cred);
CREATE INDEX idx_tx_out_stake_address_id ON public.tx_out USING btree (stake_address_id);
CREATE INDEX idx_tx_out_tx_id ON public.tx_out USING btree (tx_id);
CREATE INDEX tx_out_inline_datum_id_idx ON public.tx_out USING btree (inline_datum_id);
CREATE INDEX tx_out_reference_script_id_idx ON public.tx_out USING btree (reference_script_id);


-- public.voting_anchor definition

-- Drop table

-- DROP TABLE public.voting_anchor;

CREATE TABLE public.voting_anchor ( id bigserial NOT NULL, url varchar NOT NULL, data_hash bytea NOT NULL, "type" public."anchortype" NOT NULL, block_id int8 NOT NULL, CONSTRAINT unique_voting_anchor UNIQUE (data_hash, url, type), CONSTRAINT voting_anchor_pkey PRIMARY KEY (id));


-- public.voting_procedure definition

-- Drop table

-- DROP TABLE public.voting_procedure;

CREATE TABLE public.voting_procedure ( id bigserial NOT NULL, tx_id int8 NOT NULL, "index" int4 NOT NULL, gov_action_proposal_id int8 NOT NULL, voter_role public."voterrole" NOT NULL, drep_voter int8 NULL, pool_voter int8 NULL, "vote" public."vote" NOT NULL, voting_anchor_id int8 NULL, committee_voter int8 NULL, invalid int8 NULL, CONSTRAINT voting_procedure_pkey PRIMARY KEY (id));


-- public.withdrawal definition

-- Drop table

-- DROP TABLE public.withdrawal;

CREATE TABLE public.withdrawal ( id bigserial NOT NULL, addr_id int8 NOT NULL, amount public."lovelace" NOT NULL, redeemer_id int8 NULL, tx_id int8 NOT NULL, CONSTRAINT withdrawal_pkey PRIMARY KEY (id));
CREATE INDEX idx_withdrawal_addr_id ON public.withdrawal USING btree (addr_id);
CREATE INDEX idx_withdrawal_redeemer_id ON public.withdrawal USING btree (redeemer_id);
CREATE INDEX idx_withdrawal_tx_id ON public.withdrawal USING btree (tx_id);
CREATE UNIQUE INDEX unique_withdrawal ON public.withdrawal USING btree (addr_id, tx_id);


-- public.committee_member definition

-- Drop table

-- DROP TABLE public.committee_member;

CREATE TABLE public.committee_member ( id bigserial NOT NULL, committee_id int8 NOT NULL, committee_hash_id int8 NOT NULL, expiration_epoch public."word31type" NOT NULL, CONSTRAINT committee_member_pkey PRIMARY KEY (id), CONSTRAINT committee_member_committee_id_fkey FOREIGN KEY (committee_id) REFERENCES public.committee(id) ON DELETE CASCADE ON UPDATE RESTRICT);
CREATE INDEX idx_committee_member_committee_id ON public.committee_member USING btree (committee_id);


-- public.pg_stat_statements source

CREATE OR REPLACE VIEW public.pg_stat_statements
AS SELECT pg_stat_statements.userid,
    pg_stat_statements.dbid,
    pg_stat_statements.toplevel,
    pg_stat_statements.queryid,
    pg_stat_statements.query,
    pg_stat_statements.plans,
    pg_stat_statements.total_plan_time,
    pg_stat_statements.min_plan_time,
    pg_stat_statements.max_plan_time,
    pg_stat_statements.mean_plan_time,
    pg_stat_statements.stddev_plan_time,
    pg_stat_statements.calls,
    pg_stat_statements.total_exec_time,
    pg_stat_statements.min_exec_time,
    pg_stat_statements.max_exec_time,
    pg_stat_statements.mean_exec_time,
    pg_stat_statements.stddev_exec_time,
    pg_stat_statements.rows,
    pg_stat_statements.shared_blks_hit,
    pg_stat_statements.shared_blks_read,
    pg_stat_statements.shared_blks_dirtied,
    pg_stat_statements.shared_blks_written,
    pg_stat_statements.local_blks_hit,
    pg_stat_statements.local_blks_read,
    pg_stat_statements.local_blks_dirtied,
    pg_stat_statements.local_blks_written,
    pg_stat_statements.temp_blks_read,
    pg_stat_statements.temp_blks_written,
    pg_stat_statements.blk_read_time,
    pg_stat_statements.blk_write_time,
    pg_stat_statements.wal_records,
    pg_stat_statements.wal_fpi,
    pg_stat_statements.wal_bytes
   FROM pg_stat_statements(true) pg_stat_statements(userid, dbid, toplevel, queryid, query, plans, total_plan_time, min_plan_time, max_plan_time, mean_plan_time, stddev_plan_time, calls, total_exec_time, min_exec_time, max_exec_time, mean_exec_time, stddev_exec_time, rows, shared_blks_hit, shared_blks_read, shared_blks_dirtied, shared_blks_written, local_blks_hit, local_blks_read, local_blks_dirtied, local_blks_written, temp_blks_read, temp_blks_written, blk_read_time, blk_write_time, wal_records, wal_fpi, wal_bytes);


-- public.pg_stat_statements_info source

CREATE OR REPLACE VIEW public.pg_stat_statements_info
AS SELECT pg_stat_statements_info.dealloc,
    pg_stat_statements_info.stats_reset
   FROM pg_stat_statements_info() pg_stat_statements_info(dealloc, stats_reset);


-- public.utxo_byron_view source

CREATE OR REPLACE VIEW public.utxo_byron_view
AS SELECT tx_out.id,
    tx_out.tx_id,
    tx_out.index,
    tx_out.address,
    tx_out.address_has_script,
    tx_out.payment_cred,
    tx_out.stake_address_id,
    tx_out.value,
    tx_out.data_hash,
    tx_out.inline_datum_id,
    tx_out.reference_script_id,
    tx_out.consumed_by_tx_id
   FROM tx_out
     LEFT JOIN tx_in ON tx_out.tx_id = tx_in.tx_out_id AND tx_out.index::smallint = tx_in.tx_out_index::smallint
  WHERE tx_in.tx_in_id IS NULL;


-- public.utxo_view source

CREATE OR REPLACE VIEW public.utxo_view
AS SELECT tx_out.id,
    tx_out.tx_id,
    tx_out.index,
    tx_out.address,
    tx_out.address_has_script,
    tx_out.payment_cred,
    tx_out.stake_address_id,
    tx_out.value,
    tx_out.data_hash,
    tx_out.inline_datum_id,
    tx_out.reference_script_id,
    tx_out.consumed_by_tx_id
   FROM tx_out
     LEFT JOIN tx_in ON tx_out.tx_id = tx_in.tx_out_id AND tx_out.index::smallint = tx_in.tx_out_index::smallint
     LEFT JOIN tx ON tx.id = tx_out.tx_id
     LEFT JOIN block ON tx.block_id = block.id
  WHERE tx_in.tx_in_id IS NULL AND block.epoch_no IS NOT NULL;



-- DROP FUNCTION public.pg_stat_statements(in bool, out oid, out oid, out bool, out int8, out text, out int8, out float8, out float8, out float8, out float8, out float8, out int8, out float8, out float8, out float8, out float8, out float8, out int8, out int8, out int8, out int8, out int8, out int8, out int8, out int8, out int8, out int8, out int8, out float8, out float8, out int8, out int8, out numeric);

CREATE OR REPLACE FUNCTION public.pg_stat_statements(showtext boolean, OUT userid oid, OUT dbid oid, OUT toplevel boolean, OUT queryid bigint, OUT query text, OUT plans bigint, OUT total_plan_time double precision, OUT min_plan_time double precision, OUT max_plan_time double precision, OUT mean_plan_time double precision, OUT stddev_plan_time double precision, OUT calls bigint, OUT total_exec_time double precision, OUT min_exec_time double precision, OUT max_exec_time double precision, OUT mean_exec_time double precision, OUT stddev_exec_time double precision, OUT rows bigint, OUT shared_blks_hit bigint, OUT shared_blks_read bigint, OUT shared_blks_dirtied bigint, OUT shared_blks_written bigint, OUT local_blks_hit bigint, OUT local_blks_read bigint, OUT local_blks_dirtied bigint, OUT local_blks_written bigint, OUT temp_blks_read bigint, OUT temp_blks_written bigint, OUT blk_read_time double precision, OUT blk_write_time double precision, OUT wal_records bigint, OUT wal_fpi bigint, OUT wal_bytes numeric)
 RETURNS SETOF record
 LANGUAGE c
 PARALLEL SAFE STRICT
AS '$libdir/pg_stat_statements', $function$pg_stat_statements_1_9$function$
;

-- DROP FUNCTION public.pg_stat_statements_info(out int8, out timestamptz);

CREATE OR REPLACE FUNCTION public.pg_stat_statements_info(OUT dealloc bigint, OUT stats_reset timestamp with time zone)
 RETURNS record
 LANGUAGE c
 PARALLEL SAFE STRICT
AS '$libdir/pg_stat_statements', $function$pg_stat_statements_info$function$
;

-- DROP FUNCTION public.pg_stat_statements_reset(oid, oid, int8);

CREATE OR REPLACE FUNCTION public.pg_stat_statements_reset(userid oid DEFAULT 0, dbid oid DEFAULT 0, queryid bigint DEFAULT 0)
 RETURNS void
 LANGUAGE c
 PARALLEL SAFE STRICT
AS '$libdir/pg_stat_statements', $function$pg_stat_statements_reset_1_7$function$
;

-- DROP FUNCTION public.user_search(text);

CREATE OR REPLACE FUNCTION public.user_search(uname text)
 RETURNS TABLE(usename name, passwd text)
 LANGUAGE sql
 SECURITY DEFINER
AS $function$
  SELECT usename, passwd FROM pg_shadow WHERE usename=uname;
$function$
;
