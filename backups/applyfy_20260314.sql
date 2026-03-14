--
-- PostgreSQL database dump
--

\restrict OSDGyxRpP3tPFc0TfLkVHwll3XqwlSrKIkcrW8U805nBj7FtFqIXfa70g99fUPT

-- Dumped from database version 15.15 (Ubuntu 15.15-1.pgdg22.04+1)
-- Dumped by pg_dump version 15.15 (Ubuntu 15.15-1.pgdg22.04+1)

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: applyfy_offer_producer; Type: TABLE; Schema: public; Owner: applyfy
--

CREATE TABLE public.applyfy_offer_producer (
    offer_code text NOT NULL,
    producer_id text NOT NULL,
    producer_name text,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.applyfy_offer_producer OWNER TO applyfy;

--
-- Name: applyfy_producer_taxes; Type: TABLE; Schema: public; Owner: applyfy
--

CREATE TABLE public.applyfy_producer_taxes (
    producer_id text NOT NULL,
    email text,
    taxes_snapshot jsonb DEFAULT '{}'::jsonb NOT NULL,
    fetched_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.applyfy_producer_taxes OWNER TO applyfy;

--
-- Name: applyfy_transactions; Type: TABLE; Schema: public; Owner: applyfy
--

CREATE TABLE public.applyfy_transactions (
    id integer NOT NULL,
    transaction_id text NOT NULL,
    event text NOT NULL,
    offer_code text,
    producer_id text,
    payload jsonb NOT NULL,
    received_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.applyfy_transactions OWNER TO applyfy;

--
-- Name: applyfy_transactions_id_seq; Type: SEQUENCE; Schema: public; Owner: applyfy
--

CREATE SEQUENCE public.applyfy_transactions_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.applyfy_transactions_id_seq OWNER TO applyfy;

--
-- Name: applyfy_transactions_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: applyfy
--

ALTER SEQUENCE public.applyfy_transactions_id_seq OWNED BY public.applyfy_transactions.id;


--
-- Name: export_runs; Type: TABLE; Schema: public; Owner: applyfy
--

CREATE TABLE public.export_runs (
    id integer NOT NULL,
    run_at timestamp with time zone DEFAULT now() NOT NULL,
    rows_count integer NOT NULL,
    ok_count integer NOT NULL,
    timeout_count integer NOT NULL,
    erro_count integer NOT NULL,
    data jsonb NOT NULL
);


ALTER TABLE public.export_runs OWNER TO applyfy;

--
-- Name: export_runs_id_seq; Type: SEQUENCE; Schema: public; Owner: applyfy
--

CREATE SEQUENCE public.export_runs_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.export_runs_id_seq OWNER TO applyfy;

--
-- Name: export_runs_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: applyfy
--

ALTER SEQUENCE public.export_runs_id_seq OWNED BY public.export_runs.id;


--
-- Name: financeiro_categorias; Type: TABLE; Schema: public; Owner: applyfy
--

CREATE TABLE public.financeiro_categorias (
    id integer NOT NULL,
    nome text NOT NULL,
    tipo text NOT NULL,
    ativa boolean DEFAULT true NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT financeiro_categorias_tipo_check CHECK ((tipo = ANY (ARRAY['receita'::text, 'despesa'::text])))
);


ALTER TABLE public.financeiro_categorias OWNER TO applyfy;

--
-- Name: financeiro_categorias_id_seq; Type: SEQUENCE; Schema: public; Owner: applyfy
--

CREATE SEQUENCE public.financeiro_categorias_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.financeiro_categorias_id_seq OWNER TO applyfy;

--
-- Name: financeiro_categorias_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: applyfy
--

ALTER SEQUENCE public.financeiro_categorias_id_seq OWNED BY public.financeiro_categorias.id;


--
-- Name: financeiro_lancamentos; Type: TABLE; Schema: public; Owner: applyfy
--

CREATE TABLE public.financeiro_lancamentos (
    id integer NOT NULL,
    data date NOT NULL,
    valor numeric(16,2) NOT NULL,
    tipo text NOT NULL,
    categoria_id integer,
    descricao text,
    natureza_dfc text,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT financeiro_lancamentos_natureza_dfc_check CHECK ((natureza_dfc = ANY (ARRAY['operacional'::text, 'investimento'::text, 'financiamento'::text]))),
    CONSTRAINT financeiro_lancamentos_tipo_check CHECK ((tipo = ANY (ARRAY['receita'::text, 'despesa'::text])))
);


ALTER TABLE public.financeiro_lancamentos OWNER TO applyfy;

--
-- Name: financeiro_lancamentos_id_seq; Type: SEQUENCE; Schema: public; Owner: applyfy
--

CREATE SEQUENCE public.financeiro_lancamentos_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.financeiro_lancamentos_id_seq OWNER TO applyfy;

--
-- Name: financeiro_lancamentos_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: applyfy
--

ALTER SEQUENCE public.financeiro_lancamentos_id_seq OWNED BY public.financeiro_lancamentos.id;


--
-- Name: saldos_historico; Type: TABLE; Schema: public; Owner: applyfy
--

CREATE TABLE public.saldos_historico (
    run_at timestamp with time zone NOT NULL,
    email text NOT NULL,
    nome text NOT NULL,
    saldo_pendente numeric(16,2) DEFAULT 0 NOT NULL,
    saldo_retido numeric(16,2) DEFAULT 0 NOT NULL,
    saldo_disponivel numeric(16,2) DEFAULT 0 NOT NULL,
    total_sacado numeric(16,2) DEFAULT 0 NOT NULL,
    vendas_liquidas numeric(16,2) DEFAULT 0 NOT NULL,
    indicacao numeric(16,2) DEFAULT 0 NOT NULL,
    outros numeric(16,2) DEFAULT 0 NOT NULL
);


ALTER TABLE public.saldos_historico OWNER TO applyfy;

--
-- Name: applyfy_transactions id; Type: DEFAULT; Schema: public; Owner: applyfy
--

ALTER TABLE ONLY public.applyfy_transactions ALTER COLUMN id SET DEFAULT nextval('public.applyfy_transactions_id_seq'::regclass);


--
-- Name: export_runs id; Type: DEFAULT; Schema: public; Owner: applyfy
--

ALTER TABLE ONLY public.export_runs ALTER COLUMN id SET DEFAULT nextval('public.export_runs_id_seq'::regclass);


--
-- Name: financeiro_categorias id; Type: DEFAULT; Schema: public; Owner: applyfy
--

ALTER TABLE ONLY public.financeiro_categorias ALTER COLUMN id SET DEFAULT nextval('public.financeiro_categorias_id_seq'::regclass);


--
-- Name: financeiro_lancamentos id; Type: DEFAULT; Schema: public; Owner: applyfy
--

ALTER TABLE ONLY public.financeiro_lancamentos ALTER COLUMN id SET DEFAULT nextval('public.financeiro_lancamentos_id_seq'::regclass);


--
-- Data for Name: applyfy_offer_producer; Type: TABLE DATA; Schema: public; Owner: applyfy
--

COPY public.applyfy_offer_producer (offer_code, producer_id, producer_name, updated_at) FROM stdin;
\.


--
-- Data for Name: applyfy_producer_taxes; Type: TABLE DATA; Schema: public; Owner: applyfy
--

COPY public.applyfy_producer_taxes (producer_id, email, taxes_snapshot, fetched_at) FROM stdin;
\.


--
-- Data for Name: applyfy_transactions; Type: TABLE DATA; Schema: public; Owner: applyfy
--

COPY public.applyfy_transactions (id, transaction_id, event, offer_code, producer_id, payload, received_at) FROM stdin;
1	cmmqqw5xw05dd1rp47jjg8ws5	TRANSACTION_CREATED	H0TXXY5	\N	{"event": "TRANSACTION_CREATED", "token": "nnsgh0ys", "client": {"id": "cmmqqvjba02b31yrumqk8dw3i", "cpf": "054.293.303-96", "cnpj": null, "name": "Neuciane Rubens ", "email": "neucianerubens91@gmail.com", "phone": "+5588992186391", "address": null}, "offerCode": "H0TXXY5", "orderItems": [{"id": "cmmqqw5w705d11rp4399p5kjp", "price": 14.9, "product": {"id": "cmm9lkvhh01eg1yruk8acisyk", "name": "Cativantes Cardapio", "externalId": null}}], "trackProps": {"ip": "186.227.68.177", "fbc": "fb.2.1773518111984.PAZXh0bgNhZW0BMABhZGlkAaswV5v52YZzcnRjBmFwcF9pZA8xMjQwMjQ1NzQyODc0MTQAAafMPEJl3YGJAf6DTeD7U_8HC5HRcNzZyngsuAHeumEmNpS9qYsMCCCPoIXw7w_aem_M7SJjuuaxJsf_Hn25NiCaw", "fbp": "fb.2.1773518111987.333245420674079117", "utm_id": "120242797911950742", "isUpsell": false, "utm_term": "CONJUNTO+04", "user_agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 18_7 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/23D127 Instagram 420.0.0.39.76 (iPhone12,1; iOS 26_3; pt_BR; pt; scale=2.00; 828x1792; IABMV/1; 904620799) Safari/604.1", "utm_medium": "Instagram_Stories", "utm_source": "ig", "utm_content": "CRIATIVO+01", "utm_campaign": "[ABO]+CARDAPIO+1-1-1-+[04-03]"}, "transaction": {"id": "cmmqqw5xw05dd1rp47jjg8ws5", "amount": 14.9, "status": "PENDING", "payedAt": null, "acquirer": "Pagar.me", "currency": "BRL", "producer": {"id": "cmm9irpi500i51rpbx5z05nll", "name": "Talita Lorraine de Lima Mendes", "email": "talitalorraine2002@gmail.com", "phone": "(31) 99559-8475"}, "createdAt": "2026-03-14T19:55:12.758Z", "identifier": "app.applyfy.com.br-ORDER-cmmqqw5vz05d01rp4raw0p71d", "chargeAmount": 14.9, "exchangeRate": 1, "installments": 1, "paymentMethod": "PIX", "originalAmount": 14.9, "pixInformation": {"id": "cmmqqw7h605dh1rp48kca9wjn", "image": "https://api.pagar.me/core/v5/transactions/tran_Pv5Mo9KidycPYNzb/qrcode?payment_method=pix", "qrCode": "00020101021226820014br.gov.bcb.pix2560pix.stone.com.br/pix/v2/4ba61755-eaf6-4f1c-81a5-ca0d02dda790520400005303986540514.905802BR5925Pagar Me Instituicao De P6014RIO DE JANEIRO6229052573195976dc6badb07e708c887630446D9", "createdAt": "2026-03-14T19:55:14.765Z", "expiresAt": null, "updatedAt": "2026-03-14T19:55:14.765Z", "endToEndId": null, "description": null, "transactionId": "cmmqqw5xw05dd1rp47jjg8ws5"}, "originalCurrency": "BRL", "boletoInformation": null}, "subscription": null}	2026-03-14 19:55:16.033379+00
2	cmmqqwa6c05dy1rp45hc32obf	TRANSACTION_PAID	SWIMMMR	\N	{"event": "TRANSACTION_PAID", "token": "nnsgh0ys", "client": {"id": "cmmqqrmqe02931yru2hwvq26t", "cpf": "320.622.988-03", "cnpj": null, "name": "Valéria Aparecida dos Santos ", "email": "valeriasantosmkt@yahoo.com", "phone": "+5535999559974", "address": null}, "offerCode": "SWIMMMR", "orderItems": [{"id": "cmmqqwa5b05dr1rp4zmchm11a", "price": 29.9, "product": {"id": "cmk2j2lvd07lxqr1rjbjz1kvq", "name": "SUPORTE VIP INDIVIDUAL", "externalId": null}}, {"id": "cmmqqwa5b05ds1rp420wvirfl", "price": 19.9, "product": {"id": "cmk2k0c3q07u0qr1rnv4rb818", "name": "ACESSO VITALÍCIO", "externalId": null}}, {"id": "cmmqqwa5b05dt1rp4cgci83ho", "price": 97.99, "product": {"id": "cmk2o96af074vqo1kt650u9ci", "name": "PROSPERA 360", "externalId": null}}], "trackProps": {"ip": "138.94.52.239", "fbp": "fb.2.1773517756605.18830249956621826", "isUpsell": false, "user_agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Mobile Safari/537.36"}, "transaction": {"id": "cmmqqwa6c05dy1rp45hc32obf", "amount": 147.79, "status": "COMPLETED", "payedAt": "2026-03-14T19:55:24.522Z", "acquirer": "Pagar.me", "currency": "BRL", "producer": {"id": "cmjwvvb4h0ix1lh1kcbpu3eyr", "name": "rafaela carla justino", "email": "rafaelacjustinopm360@gmail.com", "phone": "(16) 99210-2332"}, "createdAt": "2026-03-14T19:55:18.267Z", "identifier": "app.applyfy.com.br-ORDER-cmmqqwa5305dq1rp46ygbbtdt", "chargeAmount": 172.41, "exchangeRate": 1, "installments": 7, "paymentMethod": "CREDIT_CARD", "originalAmount": 147.79, "pixInformation": null, "originalCurrency": "BRL", "boletoInformation": null}, "subscription": null}	2026-03-14 19:55:25.401157+00
3	tx-SESSION_CREATED-	SESSION_CREATED	\N	\N	{"data": {"client": null, "orderId": null, "producer": {"id": "cmdomywys009lxfvof3wbykp7", "name": "Pedro Henrique Carneiro Frade", "email": "pedrofrade@outlook.com", "phone": "(11) 91740-8090"}, "productId": "cmkcqole50h9iqi1ktpni4ud2", "checkoutId": "cmkcqole50h9jqi1k2y0k7cio"}, "event": "SESSION_CREATED", "token": "nnsgh0ys", "isRecovered": false, "checkoutSessionGuid": "019cedea-f58d-70bb-bf48-e92107d17344", "checkoutSessionStatus": "ACTIVE", "checkoutSessionUpdatedAt": "2026-03-14T19:55:24.423Z"}	2026-03-14 19:55:25.626122+00
4	tx-SESSION_UPDATED-	SESSION_UPDATED	\N	\N	{"data": {"client": {"id": "cmmqqrmqe02931yru2hwvq26t", "cpf": "320.622.988-03", "cnpj": null, "name": "Valéria Aparecida dos Santos ", "email": "valeriasantosmkt@yahoo.com", "phone": "+5535999559974"}, "orderId": "cmmqqwa5305dq1rp46ygbbtdt", "producer": {"id": "cmjwvvb4h0ix1lh1kcbpu3eyr", "name": "rafaela carla justino", "email": "rafaelacjustinopm360@gmail.com", "phone": "(16) 99210-2332"}, "productId": "cmk2o96af074vqo1kt650u9ci", "checkoutId": "cmk2o96af074wqo1khrbn6kcd"}, "event": "SESSION_UPDATED", "token": "nnsgh0ys", "isRecovered": false, "checkoutSessionGuid": "019cede5-4ebe-775c-bf51-f5b6aaa09510", "checkoutSessionStatus": "FINISHED", "checkoutSessionUpdatedAt": "2026-03-14T19:55:27.018Z"}	2026-03-14 19:55:28.218152+00
8	cmmqqw5xw05dd1rp47jjg8ws5	TRANSACTION_PAID	H0TXXY5	\N	{"event": "TRANSACTION_PAID", "token": "nnsgh0ys", "client": {"id": "cmmqqvjba02b31yrumqk8dw3i", "cpf": "054.293.303-96", "cnpj": null, "name": "Neuciane Rubens ", "email": "neucianerubens91@gmail.com", "phone": "+5588992186391", "address": null}, "offerCode": "H0TXXY5", "orderItems": [{"id": "cmmqqw5w705d11rp4399p5kjp", "price": 14.9, "product": {"id": "cmm9lkvhh01eg1yruk8acisyk", "name": "Cativantes Cardapio", "externalId": null}}], "trackProps": {"ip": "186.227.68.177", "fbc": "fb.2.1773518111984.PAZXh0bgNhZW0BMABhZGlkAaswV5v52YZzcnRjBmFwcF9pZA8xMjQwMjQ1NzQyODc0MTQAAafMPEJl3YGJAf6DTeD7U_8HC5HRcNzZyngsuAHeumEmNpS9qYsMCCCPoIXw7w_aem_M7SJjuuaxJsf_Hn25NiCaw", "fbp": "fb.2.1773518111987.333245420674079117", "utm_id": "120242797911950742", "isUpsell": false, "utm_term": "CONJUNTO+04", "user_agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 18_7 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/23D127 Instagram 420.0.0.39.76 (iPhone12,1; iOS 26_3; pt_BR; pt; scale=2.00; 828x1792; IABMV/1; 904620799) Safari/604.1", "utm_medium": "Instagram_Stories", "utm_source": "ig", "utm_content": "CRIATIVO+01", "utm_campaign": "[ABO]+CARDAPIO+1-1-1-+[04-03]"}, "transaction": {"id": "cmmqqw5xw05dd1rp47jjg8ws5", "amount": 14.9, "status": "COMPLETED", "payedAt": "2026-03-14T19:57:49.048Z", "acquirer": "Pagar.me", "currency": "BRL", "producer": {"id": "cmm9irpi500i51rpbx5z05nll", "name": "Talita Lorraine de Lima Mendes", "email": "talitalorraine2002@gmail.com", "phone": "(31) 99559-8475"}, "createdAt": "2026-03-14T19:55:12.758Z", "identifier": "app.applyfy.com.br-ORDER-cmmqqw5vz05d01rp4raw0p71d", "chargeAmount": 14.9, "exchangeRate": 1, "installments": 1, "paymentMethod": "PIX", "originalAmount": 14.9, "pixInformation": {"id": "cmmqqw7h605dh1rp48kca9wjn", "image": "https://api.pagar.me/core/v5/transactions/tran_Pv5Mo9KidycPYNzb/qrcode?payment_method=pix", "qrCode": "00020101021226820014br.gov.bcb.pix2560pix.stone.com.br/pix/v2/4ba61755-eaf6-4f1c-81a5-ca0d02dda790520400005303986540514.905802BR5925Pagar Me Instituicao De P6014RIO DE JANEIRO6229052573195976dc6badb07e708c887630446D9", "createdAt": "2026-03-14T19:55:14.765Z", "expiresAt": null, "updatedAt": "2026-03-14T19:55:14.765Z", "endToEndId": null, "description": null, "transactionId": "cmmqqw5xw05dd1rp47jjg8ws5"}, "originalCurrency": "BRL", "boletoInformation": null}, "subscription": null}	2026-03-14 19:57:49.63539+00
9	cmmqr0ba902cl1yruqkflbpo5	TRANSACTION_CREATED	SWIMMMR	\N	{"event": "TRANSACTION_CREATED", "token": "nnsgh0ys", "client": {"id": "cmmqqyiaa02ac1rru5me637cb", "cpf": "286.362.498-99", "cnpj": null, "name": "Rosangela de Macena Leite", "email": "rosangellamacena@outlook.com", "phone": "+5511989155585", "address": null}, "offerCode": "SWIMMMR", "orderItems": [{"id": "cmmqr0b8p02cg1yrue16fbyxs", "price": 97.99, "product": {"id": "cmk2o96af074vqo1kt650u9ci", "name": "PROSPERA 360", "externalId": null}}], "trackProps": {"ip": "187.43.130.173", "fbp": "fb.2.1773518211789.76637133065463157", "isUpsell": false, "user_agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) SamsungBrowser/29.0 Chrome/136.0.0.0 Mobile Safari/537.36"}, "transaction": {"id": "cmmqr0ba902cl1yruqkflbpo5", "amount": 97.99, "status": "PENDING", "payedAt": null, "acquirer": "Pagar.me", "currency": "BRL", "producer": {"id": "cmjwvvb4h0ix1lh1kcbpu3eyr", "name": "rafaela carla justino", "email": "rafaelacjustinopm360@gmail.com", "phone": "(16) 99210-2332"}, "createdAt": "2026-03-14T19:58:26.306Z", "identifier": "app.applyfy.com.br-ORDER-cmmqr0b8j02cf1yru0x483y33", "chargeAmount": 97.99, "exchangeRate": 1, "installments": 1, "paymentMethod": "PIX", "originalAmount": 97.99, "pixInformation": {"id": "cmmqr0cls02cp1yruagub7icc", "image": "https://api.pagar.me/core/v5/transactions/tran_r29OkoLudKS9AOED/qrcode?payment_method=pix", "qrCode": "00020101021226820014br.gov.bcb.pix2560pix.stone.com.br/pix/v2/8d7c47c0-21b8-401f-9470-4b7a85777ce5520400005303986540597.995802BR5925Pagar Me Instituicao De P6014RIO DE JANEIRO6229052585019c02b4856092f79639be8630493B8", "createdAt": "2026-03-14T19:58:28.032Z", "expiresAt": null, "updatedAt": "2026-03-14T19:58:28.032Z", "endToEndId": null, "description": null, "transactionId": "cmmqr0ba902cl1yruqkflbpo5"}, "originalCurrency": "BRL", "boletoInformation": null}, "subscription": null}	2026-03-14 19:58:28.960655+00
11	cmmqr0wqb02au1rru2zge308l	TRANSACTION_CREATED	P75L8Q8	\N	{"event": "TRANSACTION_CREATED", "token": "nnsgh0ys", "client": {"id": "cmmqr052t02aq1rruztw2pnxy", "cpf": "026.035.201-21", "cnpj": null, "name": "Priscila Karen Smith ", "email": "prismith89@gmail.com", "phone": "+5565999722634", "address": null}, "offerCode": "P75L8Q8", "orderItems": [{"id": "cmmqr0wpf02as1rrufsbam8mg", "price": 34, "product": {"id": "cmg80wou103t659i3p55lu35d", "name": "LUCRANDO COM A SHÔ", "externalId": null}}], "trackProps": {"ip": "138.0.251.107", "fbc": "fb.2.1773518292839.PAZXh0bgNhZW0CMTAAc3J0YwZhcHBfaWQPMTI0MDI0NTc0Mjg3NDE0AAGn95bEDP-pqtgFnU4Q4liKYRrWisv0JHsCN-iwM2JB52uCD2-vAmYxPlMdIW8_aem_M-24IQpBeiRC_Hl-pVEOcQ", "fbp": "fb.2.1773518094931.319583658432834161", "isUpsell": false, "user_agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 18_7 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/23D8133 Instagram 420.0.0.39.76 (iPhone14,7; iOS 26_3_1; pt_PT; pt-PT; scale=3.00; 1170x2532; IABMV/1; 904620799) Safari/604.1"}, "transaction": {"id": "cmmqr0wqb02au1rru2zge308l", "amount": 34, "status": "PENDING", "payedAt": null, "acquirer": "Pagar.me", "currency": "BRL", "producer": {"id": "cmccde86a0ek8ikxtoaw52r76", "name": "Júlia Pereira Cardozo ", "email": "juliacardozomkt@gmail.com", "phone": "(51) 98947-0504"}, "createdAt": "2026-03-14T19:58:54.125Z", "identifier": "app.applyfy.com.br-ORDER-cmmqr0wp802ar1rrukokz6xem", "chargeAmount": 34, "exchangeRate": 1, "installments": 1, "paymentMethod": "PIX", "originalAmount": 34, "pixInformation": {"id": "cmmqr0y9202b21rru3cx9c56j", "image": "https://api.pagar.me/core/v5/transactions/tran_NaeMAy0uwOUk6ogY/qrcode?payment_method=pix", "qrCode": "00020101021226820014br.gov.bcb.pix2560pix.stone.com.br/pix/v2/e87b01f2-127e-49e8-bd27-ec34c052f861520400005303986540534.005802BR5925Pagar Me Instituicao De P6014RIO DE JANEIRO62290525ee1318844fb545f1b20359a9963041752", "createdAt": "2026-03-14T19:58:56.088Z", "expiresAt": null, "updatedAt": "2026-03-14T19:58:56.088Z", "endToEndId": null, "description": null, "transactionId": "cmmqr0wqb02au1rru2zge308l"}, "originalCurrency": "BRL", "boletoInformation": null}, "subscription": null}	2026-03-14 19:58:56.988215+00
14	cmmqr0wqb02au1rru2zge308l	TRANSACTION_PAID	P75L8Q8	\N	{"event": "TRANSACTION_PAID", "token": "nnsgh0ys", "client": {"id": "cmmqr052t02aq1rruztw2pnxy", "cpf": "026.035.201-21", "cnpj": null, "name": "Priscila Karen Smith ", "email": "prismith89@gmail.com", "phone": "+5565999722634", "address": null}, "offerCode": "P75L8Q8", "orderItems": [{"id": "cmmqr0wpf02as1rrufsbam8mg", "price": 34, "product": {"id": "cmg80wou103t659i3p55lu35d", "name": "LUCRANDO COM A SHÔ", "externalId": null}}], "trackProps": {"ip": "138.0.251.107", "fbc": "fb.2.1773518292839.PAZXh0bgNhZW0CMTAAc3J0YwZhcHBfaWQPMTI0MDI0NTc0Mjg3NDE0AAGn95bEDP-pqtgFnU4Q4liKYRrWisv0JHsCN-iwM2JB52uCD2-vAmYxPlMdIW8_aem_M-24IQpBeiRC_Hl-pVEOcQ", "fbp": "fb.2.1773518094931.319583658432834161", "isUpsell": false, "user_agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 18_7 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/23D8133 Instagram 420.0.0.39.76 (iPhone14,7; iOS 26_3_1; pt_PT; pt-PT; scale=3.00; 1170x2532; IABMV/1; 904620799) Safari/604.1"}, "transaction": {"id": "cmmqr0wqb02au1rru2zge308l", "amount": 34, "status": "COMPLETED", "payedAt": "2026-03-14T20:00:50.749Z", "acquirer": "Pagar.me", "currency": "BRL", "producer": {"id": "cmccde86a0ek8ikxtoaw52r76", "name": "Júlia Pereira Cardozo ", "email": "juliacardozomkt@gmail.com", "phone": "(51) 98947-0504"}, "createdAt": "2026-03-14T19:58:54.125Z", "identifier": "app.applyfy.com.br-ORDER-cmmqr0wp802ar1rrukokz6xem", "chargeAmount": 34, "exchangeRate": 1, "installments": 1, "paymentMethod": "PIX", "originalAmount": 34, "pixInformation": {"id": "cmmqr0y9202b21rru3cx9c56j", "image": "https://api.pagar.me/core/v5/transactions/tran_NaeMAy0uwOUk6ogY/qrcode?payment_method=pix", "qrCode": "00020101021226820014br.gov.bcb.pix2560pix.stone.com.br/pix/v2/e87b01f2-127e-49e8-bd27-ec34c052f861520400005303986540534.005802BR5925Pagar Me Instituicao De P6014RIO DE JANEIRO62290525ee1318844fb545f1b20359a9963041752", "createdAt": "2026-03-14T19:58:56.088Z", "expiresAt": null, "updatedAt": "2026-03-14T19:58:56.088Z", "endToEndId": null, "description": null, "transactionId": "cmmqr0wqb02au1rru2zge308l"}, "originalCurrency": "BRL", "boletoInformation": null}, "subscription": null}	2026-03-14 20:00:51.358625+00
15	cmmqr0ba902cl1yruqkflbpo5	TRANSACTION_PAID	SWIMMMR	\N	{"event": "TRANSACTION_PAID", "token": "nnsgh0ys", "client": {"id": "cmmqqyiaa02ac1rru5me637cb", "cpf": "286.362.498-99", "cnpj": null, "name": "Rosangela de Macena Leite", "email": "rosangellamacena@outlook.com", "phone": "+5511989155585", "address": null}, "offerCode": "SWIMMMR", "orderItems": [{"id": "cmmqr0b8p02cg1yrue16fbyxs", "price": 97.99, "product": {"id": "cmk2o96af074vqo1kt650u9ci", "name": "PROSPERA 360", "externalId": null}}], "trackProps": {"ip": "187.43.130.173", "fbp": "fb.2.1773518211789.76637133065463157", "isUpsell": false, "user_agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) SamsungBrowser/29.0 Chrome/136.0.0.0 Mobile Safari/537.36"}, "transaction": {"id": "cmmqr0ba902cl1yruqkflbpo5", "amount": 97.99, "status": "COMPLETED", "payedAt": "2026-03-14T20:00:55.745Z", "acquirer": "Pagar.me", "currency": "BRL", "producer": {"id": "cmjwvvb4h0ix1lh1kcbpu3eyr", "name": "rafaela carla justino", "email": "rafaelacjustinopm360@gmail.com", "phone": "(16) 99210-2332"}, "createdAt": "2026-03-14T19:58:26.306Z", "identifier": "app.applyfy.com.br-ORDER-cmmqr0b8j02cf1yru0x483y33", "chargeAmount": 97.99, "exchangeRate": 1, "installments": 1, "paymentMethod": "PIX", "originalAmount": 97.99, "pixInformation": {"id": "cmmqr0cls02cp1yruagub7icc", "image": "https://api.pagar.me/core/v5/transactions/tran_r29OkoLudKS9AOED/qrcode?payment_method=pix", "qrCode": "00020101021226820014br.gov.bcb.pix2560pix.stone.com.br/pix/v2/8d7c47c0-21b8-401f-9470-4b7a85777ce5520400005303986540597.995802BR5925Pagar Me Instituicao De P6014RIO DE JANEIRO6229052585019c02b4856092f79639be8630493B8", "createdAt": "2026-03-14T19:58:28.032Z", "expiresAt": null, "updatedAt": "2026-03-14T19:58:28.032Z", "endToEndId": null, "description": null, "transactionId": "cmmqr0ba902cl1yruqkflbpo5"}, "originalCurrency": "BRL", "boletoInformation": null}, "subscription": null}	2026-03-14 20:00:55.994164+00
17	cmmqr4mw902bh1rruxe5707zy	TRANSACTION_CREATED	J7DA9K2	\N	{"event": "TRANSACTION_CREATED", "token": "nnsgh0ys", "client": {"id": "cmm0s9k3o023t1spoeu46m6qs", "cpf": "011.363.388-29", "cnpj": null, "name": "Neuza Neves Vieira ", "email": "joaopedroneves1319@gmail.com", "phone": "+5511981386121", "address": null}, "offerCode": "J7DA9K2", "orderItems": [{"id": "cmmqr4mus02bd1rru56znv505", "price": 3000, "product": {"id": "cmge2dijc07syisvs9duc3ne6", "name": "Grupo + Acompanhamento Exclusivo", "externalId": null}}], "trackProps": {"ip": "177.172.250.57", "isUpsell": false, "user_agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_5_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Mobile/15E148 Safari/604.1"}, "transaction": {"id": "cmmqr4mw902bh1rruxe5707zy", "amount": 3000, "status": "PENDING", "payedAt": null, "acquirer": "Pagar.me", "currency": "BRL", "producer": {"id": "cmga5fa0l00e445zpzpyyk4l8", "name": "Arthur Fernandes Santos", "email": "alexsandrosf3@gmail.com", "phone": "(31) 99946-1179"}, "createdAt": "2026-03-14T20:01:47.983Z", "identifier": "app.applyfy.com.br-ORDER-cmmqr4mug02bc1rruhc53bm17", "chargeAmount": 3835.92, "exchangeRate": 1, "installments": 12, "paymentMethod": "CREDIT_CARD", "originalAmount": 3000, "pixInformation": null, "originalCurrency": "BRL", "boletoInformation": null}, "subscription": null}	2026-03-14 20:01:55.260935+00
18	cmmqr4mw902bh1rruxe5707zy	TRANSACTION_CANCELED	J7DA9K2	\N	{"event": "TRANSACTION_CANCELED", "token": "nnsgh0ys", "client": {"id": "cmm0s9k3o023t1spoeu46m6qs", "cpf": "011.363.388-29", "cnpj": null, "name": "Neuza Neves Vieira ", "email": "joaopedroneves1319@gmail.com", "phone": "+5511981386121", "address": null}, "offerCode": "J7DA9K2", "orderItems": [{"id": "cmmqr4mus02bd1rru56znv505", "price": 3000, "product": {"id": "cmge2dijc07syisvs9duc3ne6", "name": "Grupo + Acompanhamento Exclusivo", "externalId": null}}], "trackProps": {"ip": "177.172.250.57", "isUpsell": false, "user_agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_5_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Mobile/15E148 Safari/604.1"}, "transaction": {"id": "cmmqr4mw902bh1rruxe5707zy", "amount": 3000, "status": "FAILED", "payedAt": null, "acquirer": "Pagar.me", "currency": "BRL", "producer": {"id": "cmga5fa0l00e445zpzpyyk4l8", "name": "Arthur Fernandes Santos", "email": "alexsandrosf3@gmail.com", "phone": "(31) 99946-1179"}, "createdAt": "2026-03-14T20:01:47.983Z", "identifier": "app.applyfy.com.br-ORDER-cmmqr4mug02bc1rruhc53bm17", "chargeAmount": 3835.92, "exchangeRate": 1, "installments": 12, "paymentMethod": "CREDIT_CARD", "originalAmount": 3000, "pixInformation": null, "originalCurrency": "BRL", "boletoInformation": null}, "subscription": null}	2026-03-14 20:02:05.466183+00
21	cmmqr60m802d81yruycl412pb	TRANSACTION_CREATED	AXATDYZ	\N	{"event": "TRANSACTION_CREATED", "token": "nnsgh0ys", "client": {"id": "cmmqr56cp02d11yru5fhcbyfi", "cpf": "045.980.892-37", "cnpj": null, "name": "Arlen Cristiano Dos Santos Bentes ", "email": "arlencristiano51@gmail.com", "phone": "+5593992343254", "address": null}, "offerCode": "AXATDYZ", "orderItems": [{"id": "cmmqr60jh02d31yru3slq1u3r", "price": 27.9, "product": {"id": "cmibz3i360uon10vyuzlteo9g", "name": "Mentoria Junção Milionária [START]", "externalId": null}}], "trackProps": {"ip": "148.227.122.229", "isUpsell": false, "user_agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) SamsungBrowser/29.0 Chrome/136.0.0.0 Safari/537.36", "affiliate_code": "3xmw3pq"}, "transaction": {"id": "cmmqr60m802d81yruycl412pb", "amount": 27.9, "status": "PENDING", "payedAt": null, "acquirer": "Pagar.me", "currency": "BRL", "producer": {"id": "cmga5fa0l00e445zpzpyyk4l8", "name": "Arthur Fernandes Santos", "email": "alexsandrosf3@gmail.com", "phone": "(31) 99946-1179"}, "createdAt": "2026-03-14T20:02:52.390Z", "identifier": "app.applyfy.com.br-ORDER-cmmqr60j602d21yru5nrs8vuq", "chargeAmount": 27.9, "exchangeRate": 1, "installments": 1, "paymentMethod": "PIX", "originalAmount": 27.9, "pixInformation": {"id": "cmmqr622u02dd1yruka5zdxcr", "image": "https://api.pagar.me/core/v5/transactions/tran_6kxQB45sRsRmoXK1/qrcode?payment_method=pix", "qrCode": "00020101021226820014br.gov.bcb.pix2560pix.stone.com.br/pix/v2/1318dd79-b97a-4ba5-92a6-1cbf48366342520400005303986540527.905802BR5925Pagar Me Instituicao De P6014RIO DE JANEIRO62290525bac538e394b7b4dd6ef8800a263044567", "createdAt": "2026-03-14T20:02:54.328Z", "expiresAt": null, "updatedAt": "2026-03-14T20:02:54.328Z", "endToEndId": null, "description": null, "transactionId": "cmmqr60m802d81yruycl412pb"}, "originalCurrency": "BRL", "boletoInformation": null}, "subscription": null}	2026-03-14 20:02:55.626245+00
24	tx-SESSION_ABANDONED-	SESSION_ABANDONED	\N	\N	{"data": {"client": null, "orderId": "cmmqqgatn028h1yrugq6x5m5z", "producer": {"id": "cmm188erv078y1ypt5kdv8cok", "name": "Lucas Rodrigues de Souza", "email": "lucasrdsouza1@gmail.com", "phone": "(55) 99727-9692"}, "productId": "cmm2gcath00qr1rrry34jgwis", "checkoutId": "cmm2gcatk00qs1rrrs1eeux4f"}, "event": "SESSION_ABANDONED", "token": "nnsgh0ys", "isRecovered": false, "checkoutSessionGuid": "019ceddf-7c8b-740a-a9e0-64d1da2a1473", "checkoutSessionStatus": "ABANDONED", "checkoutSessionUpdatedAt": "2026-03-14T20:03:21.991Z"}	2026-03-14 20:03:23.170832+00
27	cmmqr6ni705f71rp4jhurt5cz	TRANSACTION_PAID	UIL3WPQ	\N	{"event": "TRANSACTION_PAID", "split": {"commissions": [{"type": "product-owner", "amount": 2.19, "producerId": "cmm188erv078y1ypt5kdv8cok", "splitAccount": {"id": "cmm29yeok057t1kqvr3gp3w7d", "status": "APPROVED", "acquirer": "pagar_me", "currency": "BRL", "createdAt": "2026-02-25T16:54:35.732Z", "updatedAt": "2026-02-25T19:49:54.387Z", "customData": {}, "externalId": "re_cmm29yeyu4uxf0k9tx7enr3pn", "producerId": "cmm188erv078y1ypt5kdv8cok", "transfered": 0, "errorMessage": null, "waitingFunds": 0, "availableBalance": 0}}, {"type": "affiliate", "amount": 273.04, "producerId": "cmly98fo4085l1qqehy5as0fz", "splitAccount": {"id": "cmm3jk2vb00ai1rqqdlae77pr", "status": "APPROVED", "acquirer": "pagar_me", "currency": "BRL", "createdAt": "2026-02-26T14:11:09.575Z", "updatedAt": "2026-02-26T18:19:36.402Z", "customData": {"errorMessage": null}, "externalId": "re_cmm3jk3f6abk90l9ttfru55gv", "producerId": "cmly98fo4085l1qqehy5as0fz", "transfered": 0, "errorMessage": null, "waitingFunds": 0, "availableBalance": 0}}], "totalOwnerFee": 104.57}, "token": "nnsgh0ys", "client": {"id": "cmmqppczx024x1rruawgfewfz", "cpf": "033.941.833-82", "cnpj": null, "name": "Jorge Fernando Andrade Lima", "email": "jorgeandrademkt@gmail.com", "phone": "+5589994363428", "address": null}, "offerCode": "UIL3WPQ", "orderItems": [{"id": "cmmqr6nhg05f51rp4uwmbqh7x", "price": 297, "product": {"id": "cmm2gcath00qr1rrry34jgwis", "name": "TikTok Hub", "externalId": null}}], "trackProps": {"ip": "191.128.51.60", "isUpsell": false, "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36", "affiliate_code": "nciynpd"}, "transaction": {"id": "cmmqr6ni705f71rp4jhurt5cz", "amount": 297, "status": "COMPLETED", "payedAt": "2026-03-14T20:03:28.212Z", "acquirer": "Pagar.me", "currency": "BRL", "producer": {"id": "cmm188erv078y1ypt5kdv8cok", "name": "Lucas Rodrigues de Souza", "email": "lucasrdsouza1@gmail.com", "phone": "(55) 99727-9692"}, "createdAt": "2026-03-14T20:03:22.107Z", "identifier": "app.applyfy.com.br-ORDER-cmmqr6nh805f41rp47w8ighhw", "chargeAmount": 379.8, "exchangeRate": 1, "installments": 12, "paymentMethod": "CREDIT_CARD", "originalAmount": 297, "pixInformation": null, "originalCurrency": "BRL", "boletoInformation": null}, "subscription": null}	2026-03-14 20:03:28.838451+00
29	cmmqr60m802d81yruycl412pb	TRANSACTION_PAID	AXATDYZ	\N	{"event": "TRANSACTION_PAID", "split": {"commissions": [{"type": "product-owner", "amount": 4.1, "producerId": "cmga5fa0l00e445zpzpyyk4l8", "splitAccount": {"id": "cmgacacwd02jgnxf02f7sad9w", "status": "APPROVED", "acquirer": "pagar_me", "currency": "BRL", "createdAt": "2025-10-03T04:23:47.917Z", "updatedAt": "2025-10-03T04:23:52.352Z", "customData": {}, "externalId": "re_cmgacacq05lwu0l9t7nn0a3s6", "producerId": "cmga5fa0l00e445zpzpyyk4l8", "transfered": 0, "errorMessage": null, "waitingFunds": 0, "availableBalance": 0}}, {"type": "affiliate", "amount": 19.92, "producerId": "cmjd76jqv01gwjt1ke6ksmrtm", "splitAccount": {"id": "cmkpk62dx00x31rn0apzklww0", "status": "APPROVED", "acquirer": "pagar_me", "currency": "BRL", "createdAt": "2026-01-22T14:39:46.581Z", "updatedAt": "2026-01-22T14:40:02.296Z", "customData": {}, "externalId": "re_cmkpk62vqb7x40l9tmq8y3k59", "producerId": "cmjd76jqv01gwjt1ke6ksmrtm", "transfered": 0, "errorMessage": null, "waitingFunds": 0, "availableBalance": 0}}], "totalOwnerFee": 3.88}, "token": "nnsgh0ys", "client": {"id": "cmmqr56cp02d11yru5fhcbyfi", "cpf": "045.980.892-37", "cnpj": null, "name": "Arlen Cristiano Dos Santos Bentes ", "email": "arlencristiano51@gmail.com", "phone": "+5593992343254", "address": null}, "offerCode": "AXATDYZ", "orderItems": [{"id": "cmmqr60jh02d31yru3slq1u3r", "price": 27.9, "product": {"id": "cmibz3i360uon10vyuzlteo9g", "name": "Mentoria Junção Milionária [START]", "externalId": null}}], "trackProps": {"ip": "148.227.122.229", "isUpsell": false, "user_agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) SamsungBrowser/29.0 Chrome/136.0.0.0 Safari/537.36", "affiliate_code": "3xmw3pq"}, "transaction": {"id": "cmmqr60m802d81yruycl412pb", "amount": 27.9, "status": "COMPLETED", "payedAt": "2026-03-14T20:03:35.741Z", "acquirer": "Pagar.me", "currency": "BRL", "producer": {"id": "cmga5fa0l00e445zpzpyyk4l8", "name": "Arthur Fernandes Santos", "email": "alexsandrosf3@gmail.com", "phone": "(31) 99946-1179"}, "createdAt": "2026-03-14T20:02:52.390Z", "identifier": "app.applyfy.com.br-ORDER-cmmqr60j602d21yru5nrs8vuq", "chargeAmount": 27.9, "exchangeRate": 1, "installments": 1, "paymentMethod": "PIX", "originalAmount": 27.9, "pixInformation": {"id": "cmmqr622u02dd1yruka5zdxcr", "image": "https://api.pagar.me/core/v5/transactions/tran_6kxQB45sRsRmoXK1/qrcode?payment_method=pix", "qrCode": "00020101021226820014br.gov.bcb.pix2560pix.stone.com.br/pix/v2/1318dd79-b97a-4ba5-92a6-1cbf48366342520400005303986540527.905802BR5925Pagar Me Instituicao De P6014RIO DE JANEIRO62290525bac538e394b7b4dd6ef8800a263044567", "createdAt": "2026-03-14T20:02:54.328Z", "expiresAt": null, "updatedAt": "2026-03-14T20:02:54.328Z", "endToEndId": null, "description": null, "transactionId": "cmmqr60m802d81yruycl412pb"}, "originalCurrency": "BRL", "boletoInformation": null}, "subscription": null}	2026-03-14 20:03:36.174632+00
32	cmmqrb3zu05hz1rp4ylfuhf4r	TRANSACTION_CREATED	BYBJ1VE	\N	{"event": "TRANSACTION_CREATED", "token": "nnsgh0ys", "client": {"id": "cmmqr6rjr02cs1rruzecys0da", "cpf": "090.948.292-66", "cnpj": null, "name": "Vinícius chaves Maciel ", "email": "viniciusvinijunior272@gmail.com", "phone": "+5591910043470", "address": null}, "offerCode": "BYBJ1VE", "orderItems": [{"id": "cmmqrb3ya05hr1rp4of8nly8a", "price": 147, "product": {"id": "cmhcc2wdj0dz914dfvc05pao2", "name": "VENDA DIRETO NO AUTOMÁTICO", "externalId": null}}], "trackProps": {"ip": "74.244.223.150", "fbp": "fb.2.1773518601753.746748846206917466", "isUpsell": false, "user_agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36", "utm_medium": "bio--oti--oti_dbprh5nkbsjmmqqyr7p", "utm_source": "kwai"}, "transaction": {"id": "cmmqrb3zu05hz1rp4ylfuhf4r", "amount": 147, "status": "PENDING", "payedAt": null, "acquirer": "Pagar.me", "currency": "BRL", "producer": {"id": "cmga5fa0l00e445zpzpyyk4l8", "name": "Arthur Fernandes Santos", "email": "alexsandrosf3@gmail.com", "phone": "(31) 99946-1179"}, "createdAt": "2026-03-14T20:06:50.083Z", "identifier": "app.applyfy.com.br-ORDER-cmmqrb3y105hq1rp4polzawhn", "chargeAmount": 147, "exchangeRate": 1, "installments": 1, "paymentMethod": "PIX", "originalAmount": 147, "pixInformation": {"id": "cmmqrb5ka05i31rp4kp6a6wec", "image": "https://api.pagar.me/core/v5/transactions/tran_a5R0YodIrFmK6j9P/qrcode?payment_method=pix", "qrCode": "00020101021226820014br.gov.bcb.pix2560pix.stone.com.br/pix/v2/8fd20266-51e5-4162-bfe7-13046eaba5df5204000053039865406147.005802BR5925Pagar Me Instituicao De P6014RIO DE JANEIRO622905257e8a68fb47b36d589a400c59a6304D675", "createdAt": "2026-03-14T20:06:52.124Z", "expiresAt": null, "updatedAt": "2026-03-14T20:06:52.124Z", "endToEndId": null, "description": null, "transactionId": "cmmqrb3zu05hz1rp4ylfuhf4r"}, "originalCurrency": "BRL", "boletoInformation": null}, "subscription": null}	2026-03-14 20:06:53.059647+00
35	cmmqrfkcg05e21yp4hpjvrlef	TRANSACTION_CREATED	AXATDYZ	\N	{"event": "TRANSACTION_CREATED", "token": "nnsgh0ys", "client": {"id": "cmmqrboq102cw1rrurl31ojmk", "cpf": "115.972.713-90", "cnpj": null, "name": "João Pedro Borges da Silva ", "email": "pedrosilvaa589@mail.com", "phone": "+5534996815025", "address": null}, "offerCode": "AXATDYZ", "orderItems": [{"id": "cmmqrfkb505dx1yp46wdplug0", "price": 27.9, "product": {"id": "cmibz3i360uon10vyuzlteo9g", "name": "Mentoria Junção Milionária [START]", "externalId": null}}], "trackProps": {"ip": "186.251.77.54", "isUpsell": false, "user_agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 18_7 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/26.3 Mobile/15E148 Safari/604.1", "affiliate_code": "3xmw3pq"}, "transaction": {"id": "cmmqrfkcg05e21yp4hpjvrlef", "amount": 27.9, "status": "PENDING", "payedAt": null, "acquirer": "Pagar.me", "currency": "BRL", "producer": {"id": "cmga5fa0l00e445zpzpyyk4l8", "name": "Arthur Fernandes Santos", "email": "alexsandrosf3@gmail.com", "phone": "(31) 99946-1179"}, "createdAt": "2026-03-14T20:10:17.899Z", "identifier": "app.applyfy.com.br-ORDER-cmmqrfkax05dw1yp4q0nc8rh0", "chargeAmount": 27.9, "exchangeRate": 1, "installments": 1, "paymentMethod": "PIX", "originalAmount": 27.9, "pixInformation": {"id": "cmmqrfmjc05ep1yp4zep9td4u", "image": "https://api.pagar.me/core/v5/transactions/tran_6KoMdlC49tbxM3Y8/qrcode?payment_method=pix", "qrCode": "00020101021226820014br.gov.bcb.pix2560pix.stone.com.br/pix/v2/137360a1-9b2d-4e02-94c6-7c6798d89e7b520400005303986540527.905802BR5925Pagar Me Instituicao De P6014RIO DE JANEIRO6229052517fdd32e6a5d934e66f7f29cd6304CA50", "createdAt": "2026-03-14T20:10:20.744Z", "expiresAt": null, "updatedAt": "2026-03-14T20:10:20.744Z", "endToEndId": null, "description": null, "transactionId": "cmmqrfkcg05e21yp4hpjvrlef"}, "originalCurrency": "BRL", "boletoInformation": null}, "subscription": null}	2026-03-14 20:10:21.694834+00
36	cmmqrfkcg05e21yp4hpjvrlef	TRANSACTION_PAID	AXATDYZ	\N	{"event": "TRANSACTION_PAID", "split": {"commissions": [{"type": "product-owner", "amount": 4.1, "producerId": "cmga5fa0l00e445zpzpyyk4l8", "splitAccount": {"id": "cmgacacwd02jgnxf02f7sad9w", "status": "APPROVED", "acquirer": "pagar_me", "currency": "BRL", "createdAt": "2025-10-03T04:23:47.917Z", "updatedAt": "2025-10-03T04:23:52.352Z", "customData": {}, "externalId": "re_cmgacacq05lwu0l9t7nn0a3s6", "producerId": "cmga5fa0l00e445zpzpyyk4l8", "transfered": 0, "errorMessage": null, "waitingFunds": 0, "availableBalance": 0}}, {"type": "affiliate", "amount": 19.92, "producerId": "cmjd76jqv01gwjt1ke6ksmrtm", "splitAccount": {"id": "cmkpk62dx00x31rn0apzklww0", "status": "APPROVED", "acquirer": "pagar_me", "currency": "BRL", "createdAt": "2026-01-22T14:39:46.581Z", "updatedAt": "2026-01-22T14:40:02.296Z", "customData": {}, "externalId": "re_cmkpk62vqb7x40l9tmq8y3k59", "producerId": "cmjd76jqv01gwjt1ke6ksmrtm", "transfered": 0, "errorMessage": null, "waitingFunds": 0, "availableBalance": 0}}], "totalOwnerFee": 3.88}, "token": "nnsgh0ys", "client": {"id": "cmmqrboq102cw1rrurl31ojmk", "cpf": "115.972.713-90", "cnpj": null, "name": "João Pedro Borges da Silva ", "email": "pedrosilvaa589@mail.com", "phone": "+5534996815025", "address": null}, "offerCode": "AXATDYZ", "orderItems": [{"id": "cmmqrfkb505dx1yp46wdplug0", "price": 27.9, "product": {"id": "cmibz3i360uon10vyuzlteo9g", "name": "Mentoria Junção Milionária [START]", "externalId": null}}], "trackProps": {"ip": "186.251.77.54", "isUpsell": false, "user_agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 18_7 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/26.3 Mobile/15E148 Safari/604.1", "affiliate_code": "3xmw3pq"}, "transaction": {"id": "cmmqrfkcg05e21yp4hpjvrlef", "amount": 27.9, "status": "COMPLETED", "payedAt": "2026-03-14T20:11:10.931Z", "acquirer": "Pagar.me", "currency": "BRL", "producer": {"id": "cmga5fa0l00e445zpzpyyk4l8", "name": "Arthur Fernandes Santos", "email": "alexsandrosf3@gmail.com", "phone": "(31) 99946-1179"}, "createdAt": "2026-03-14T20:10:17.899Z", "identifier": "app.applyfy.com.br-ORDER-cmmqrfkax05dw1yp4q0nc8rh0", "chargeAmount": 27.9, "exchangeRate": 1, "installments": 1, "paymentMethod": "PIX", "originalAmount": 27.9, "pixInformation": {"id": "cmmqrfmjc05ep1yp4zep9td4u", "image": "https://api.pagar.me/core/v5/transactions/tran_6KoMdlC49tbxM3Y8/qrcode?payment_method=pix", "qrCode": "00020101021226820014br.gov.bcb.pix2560pix.stone.com.br/pix/v2/137360a1-9b2d-4e02-94c6-7c6798d89e7b520400005303986540527.905802BR5925Pagar Me Instituicao De P6014RIO DE JANEIRO6229052517fdd32e6a5d934e66f7f29cd6304CA50", "createdAt": "2026-03-14T20:10:20.744Z", "expiresAt": null, "updatedAt": "2026-03-14T20:10:20.744Z", "endToEndId": null, "description": null, "transactionId": "cmmqrfkcg05e21yp4hpjvrlef"}, "originalCurrency": "BRL", "boletoInformation": null}, "subscription": null}	2026-03-14 20:11:11.658054+00
46	cmmqrkyg905kb1rp4d2winpbq	TRANSACTION_CREATED	BYBJ1VE	\N	{"event": "TRANSACTION_CREATED", "token": "nnsgh0ys", "client": {"id": "cmmqr6rjr02cs1rruzecys0da", "cpf": "090.948.292-66", "cnpj": null, "name": "Vinícius chaves Maciel ", "email": "viniciusvinijunior272@gmail.com", "phone": "+5591910043470", "address": null}, "offerCode": "BYBJ1VE", "orderItems": [{"id": "cmmqrkydx05k31rp4tmw12dzy", "price": 147, "product": {"id": "cmhcc2wdj0dz914dfvc05pao2", "name": "VENDA DIRETO NO AUTOMÁTICO", "externalId": null}}], "trackProps": {"ip": "74.244.223.150", "fbp": "fb.2.1773518601753.746748846206917466", "isUpsell": false, "user_agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36", "utm_medium": "bio--oti--oti_dbprh5nkbsjmmqqyr7p", "utm_source": "kwai"}, "transaction": {"id": "cmmqrkyg905kb1rp4d2winpbq", "amount": 147, "status": "PENDING", "payedAt": null, "acquirer": "Pagar.me", "currency": "BRL", "producer": {"id": "cmga5fa0l00e445zpzpyyk4l8", "name": "Arthur Fernandes Santos", "email": "alexsandrosf3@gmail.com", "phone": "(31) 99946-1179"}, "createdAt": "2026-03-14T20:14:29.448Z", "identifier": "app.applyfy.com.br-ORDER-cmmqrkydq05k21rp46pljiidw", "chargeAmount": 147, "exchangeRate": 1, "installments": 1, "paymentMethod": "PIX", "originalAmount": 147, "pixInformation": {"id": "cmmqrkzno05kf1rp46qrl17m3", "image": "https://api.pagar.me/core/v5/transactions/tran_9N2rjBT4Qik8rqWK/qrcode?payment_method=pix", "qrCode": "00020101021226820014br.gov.bcb.pix2560pix.stone.com.br/pix/v2/2a2cc478-91ec-4efa-b45b-31fb2f9c93f15204000053039865406147.005802BR5925Pagar Me Instituicao De P6014RIO DE JANEIRO622905254d73cec488b9fca16a946062a63042D21", "createdAt": "2026-03-14T20:14:31.031Z", "expiresAt": null, "updatedAt": "2026-03-14T20:14:31.031Z", "endToEndId": null, "description": null, "transactionId": "cmmqrkyg905kb1rp4d2winpbq"}, "originalCurrency": "BRL", "boletoInformation": null}, "subscription": null}	2026-03-14 20:14:32.091228+00
48	cmmqrlhdk05hd1yp4lbztlhjz	TRANSACTION_CREATED	OXVCDIW	\N	{"event": "TRANSACTION_CREATED", "token": "nnsgh0ys", "client": {"id": "cmmqrjyiu05h21yp4a7hdelel", "cpf": "718.547.824-36", "cnpj": null, "name": "Lázaro Santos", "email": "lazarosantoss658ke@gmail.com", "phone": "+5581986567826", "address": null}, "offerCode": "OXVCDIW", "orderItems": [{"id": "cmmqrlhbs05h71yp47rzg3xie", "price": 147, "product": {"id": "cmgacfywz02l0jiq7w4etqdvi", "name": "Mentoria Junção Milionária", "externalId": null}}], "trackProps": {"ip": "168.121.193.37", "isUpsell": false, "user_agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Mobile Safari/537.36", "affiliate_code": "h7xrif5"}, "transaction": {"id": "cmmqrlhdk05hd1yp4lbztlhjz", "amount": 147, "status": "PENDING", "payedAt": null, "acquirer": "Pagar.me", "currency": "BRL", "producer": {"id": "cmga5fa0l00e445zpzpyyk4l8", "name": "Arthur Fernandes Santos", "email": "alexsandrosf3@gmail.com", "phone": "(31) 99946-1179"}, "createdAt": "2026-03-14T20:14:53.973Z", "identifier": "app.applyfy.com.br-ORDER-cmmqrlhbm05h61yp4beboykng", "chargeAmount": 147, "exchangeRate": 1, "installments": 1, "paymentMethod": "PIX", "originalAmount": 147, "pixInformation": {"id": "cmmqrlj4205hi1yp4ukz0v60o", "image": "https://api.pagar.me/core/v5/transactions/tran_eGnZaPAhMxuz6L85/qrcode?payment_method=pix", "qrCode": "00020101021226820014br.gov.bcb.pix2560pix.stone.com.br/pix/v2/22649fc6-79c5-475e-8fdc-0585fbdd1c055204000053039865406147.005802BR5925Pagar Me Instituicao De P6014RIO DE JANEIRO6229052595331273d9f93fc415ce8a2056304B7F2", "createdAt": "2026-03-14T20:14:56.244Z", "expiresAt": null, "updatedAt": "2026-03-14T20:14:56.244Z", "endToEndId": null, "description": null, "transactionId": "cmmqrlhdk05hd1yp4lbztlhjz"}, "originalCurrency": "BRL", "boletoInformation": null}, "subscription": null}	2026-03-14 20:14:57.227545+00
52	cmmqrlhdk05hd1yp4lbztlhjz	TRANSACTION_PAID	OXVCDIW	\N	{"event": "TRANSACTION_PAID", "split": {"commissions": [{"type": "product-owner", "amount": 26.77, "producerId": "cmga5fa0l00e445zpzpyyk4l8", "splitAccount": {"id": "cmgacacwd02jgnxf02f7sad9w", "status": "APPROVED", "acquirer": "pagar_me", "currency": "BRL", "createdAt": "2025-10-03T04:23:47.917Z", "updatedAt": "2025-10-03T04:23:52.352Z", "customData": {}, "externalId": "re_cmgacacq05lwu0l9t7nn0a3s6", "producerId": "cmga5fa0l00e445zpzpyyk4l8", "transfered": 0, "errorMessage": null, "waitingFunds": 0, "availableBalance": 0}}, {"type": "affiliate", "amount": 110.4, "producerId": "cmjd76jqv01gwjt1ke6ksmrtm", "splitAccount": {"id": "cmkpk62dx00x31rn0apzklww0", "status": "APPROVED", "acquirer": "pagar_me", "currency": "BRL", "createdAt": "2026-01-22T14:39:46.581Z", "updatedAt": "2026-01-22T14:40:02.296Z", "customData": {}, "externalId": "re_cmkpk62vqb7x40l9tmq8y3k59", "producerId": "cmjd76jqv01gwjt1ke6ksmrtm", "transfered": 0, "errorMessage": null, "waitingFunds": 0, "availableBalance": 0}}], "totalOwnerFee": 9.83}, "token": "nnsgh0ys", "client": {"id": "cmmqrjyiu05h21yp4a7hdelel", "cpf": "718.547.824-36", "cnpj": null, "name": "Lázaro Santos", "email": "lazarosantoss658ke@gmail.com", "phone": "+5581986567826", "address": null}, "offerCode": "OXVCDIW", "orderItems": [{"id": "cmmqrlhbs05h71yp47rzg3xie", "price": 147, "product": {"id": "cmgacfywz02l0jiq7w4etqdvi", "name": "Mentoria Junção Milionária", "externalId": null}}], "trackProps": {"ip": "168.121.193.37", "isUpsell": false, "user_agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Mobile Safari/537.36", "affiliate_code": "h7xrif5"}, "transaction": {"id": "cmmqrlhdk05hd1yp4lbztlhjz", "amount": 147, "status": "COMPLETED", "payedAt": "2026-03-14T20:17:47.300Z", "acquirer": "Pagar.me", "currency": "BRL", "producer": {"id": "cmga5fa0l00e445zpzpyyk4l8", "name": "Arthur Fernandes Santos", "email": "alexsandrosf3@gmail.com", "phone": "(31) 99946-1179"}, "createdAt": "2026-03-14T20:14:53.973Z", "identifier": "app.applyfy.com.br-ORDER-cmmqrlhbm05h61yp4beboykng", "chargeAmount": 147, "exchangeRate": 1, "installments": 1, "paymentMethod": "PIX", "originalAmount": 147, "pixInformation": {"id": "cmmqrlj4205hi1yp4ukz0v60o", "image": "https://api.pagar.me/core/v5/transactions/tran_eGnZaPAhMxuz6L85/qrcode?payment_method=pix", "qrCode": "00020101021226820014br.gov.bcb.pix2560pix.stone.com.br/pix/v2/22649fc6-79c5-475e-8fdc-0585fbdd1c055204000053039865406147.005802BR5925Pagar Me Instituicao De P6014RIO DE JANEIRO6229052595331273d9f93fc415ce8a2056304B7F2", "createdAt": "2026-03-14T20:14:56.244Z", "expiresAt": null, "updatedAt": "2026-03-14T20:14:56.244Z", "endToEndId": null, "description": null, "transactionId": "cmmqrlhdk05hd1yp4lbztlhjz"}, "originalCurrency": "BRL", "boletoInformation": null}, "subscription": null}	2026-03-14 20:17:47.898553+00
59	cmmqrwx8x05lx1rp4wtspog44	TRANSACTION_PAID	V52KIF0	\N	{"event": "TRANSACTION_PAID", "split": {"commissions": [{"type": "product-owner", "amount": 63.97, "producerId": "cmcf2qjxy05vzehngbs1gpd5o", "splitAccount": {"id": "cmd3kl2pe09utnxpn4m9z0cjk", "status": "APPROVED", "acquirer": "pagar_me", "currency": "BRL", "createdAt": "2025-07-14T20:42:34.610Z", "updatedAt": "2025-07-15T15:43:11.370Z", "customData": {}, "externalId": "re_cmd3kl2jf07jm0l9ttdpbrlt9", "producerId": "cmcf2qjxy05vzehngbs1gpd5o", "transfered": 0, "errorMessage": null, "waitingFunds": 0, "availableBalance": 0}}, {"type": "affiliate", "amount": 258.91, "producerId": "cmcp3izoi07o7o7r98a06twc3", "splitAccount": {"id": "cmcuoxj6w06mf108xhw5z0s7c", "status": "APPROVED", "acquirer": "pagar_me", "currency": "BRL", "createdAt": "2025-07-08T15:34:18.728Z", "updatedAt": "2025-07-08T16:51:37.413Z", "customData": {}, "externalId": "re_cmcuoxixb1wmk0l9tikf7l8rx", "producerId": "cmcp3izoi07o7o7r98a06twc3", "transfered": 0, "errorMessage": null, "waitingFunds": 0, "availableBalance": 0}}], "totalOwnerFee": 120.76}, "token": "nnsgh0ys", "client": {"id": "cmmqoxvx802181rrumi8byisy", "cpf": "073.025.546-84", "cnpj": null, "name": "Juliane Oliveira Fonseca ", "email": "julianeagroliva@outlook.com.br", "phone": "+5535988670794", "address": null}, "offerCode": "V52KIF0", "orderItems": [{"id": "cmmqrwx7c05lp1rp46cb0760s", "price": 249.9, "product": {"id": "cmckomykk00sead5y5wy8m30s", "name": "Be Your Boss", "externalId": null}}, {"id": "cmmqrwx7c05lq1rp4tytcb9zm", "price": 97, "product": {"id": "cmh51frax0cifz4w6snhorgdj", "name": "Combo Premium [Vitalício + Acelerador]", "externalId": null}}], "trackProps": {"ip": "187.60.133.29", "fbp": "fb.2.1773514809708.385914923237485802", "isUpsell": false, "user_agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 18_7 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/26.3 Mobile/15E148 Safari/604.1", "affiliate_code": "olyulks"}, "transaction": {"id": "cmmqrwx8x05lx1rp4wtspog44", "amount": 346.9, "status": "COMPLETED", "payedAt": "2026-03-14T20:23:54.004Z", "acquirer": "Pagar.me", "currency": "BRL", "producer": {"id": "cmcf2qjxy05vzehngbs1gpd5o", "name": "Camila Sobral Resende", "email": "ricardo@comunidadeboss.net", "phone": "(51) 99617-7975"}, "createdAt": "2026-03-14T20:23:47.766Z", "identifier": "app.applyfy.com.br-ORDER-cmmqrwx7305lo1rp4yghhxyn0", "chargeAmount": 443.64, "exchangeRate": 1, "installments": 12, "paymentMethod": "CREDIT_CARD", "originalAmount": 346.9, "pixInformation": null, "originalCurrency": "BRL", "boletoInformation": null}, "subscription": null}	2026-03-14 20:23:54.914371+00
67	cmmqslc4h02i31yru5n4k2vov	TRANSACTION_CREATED	F2T2Y5C	\N	{"event": "TRANSACTION_CREATED", "token": "nnsgh0ys", "client": {"id": "cmmqsjsl402ho1rruuciaqkpf", "cpf": "108.755.784-46", "cnpj": null, "name": "SAVIO GEORGE SILVA DA MATA", "email": "saviogeorgee@gmail.com", "phone": "+5584994223470", "address": null}, "offerCode": "F2T2Y5C", "orderItems": [{"id": "cmmqslc2u02hx1yruyzecanah", "price": 29, "product": {"id": "cm9m6z34300h5a8hboaj3qsr8", "name": "Combo Perfeito", "externalId": null}}], "trackProps": {"ip": "187.19.254.89", "fbp": "fb.2.1773520882327.291868839601490041", "isUpsell": false, "user_agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Mobile Safari/537.36"}, "transaction": {"id": "cmmqslc4h02i31yru5n4k2vov", "amount": 29, "status": "PENDING", "payedAt": null, "acquirer": "Pagar.me", "currency": "BRL", "producer": {"id": "cm9lsofqx00wdfsx0shnwuqwo", "name": "Vinicius Xavier", "email": "viniciusxavierbmx2016@gmail.com", "phone": "(37) 98426-6117"}, "createdAt": "2026-03-14T20:42:46.791Z", "identifier": "app.applyfy.com.br-ORDER-cmmqslc2n02hw1yrudrampf7k", "chargeAmount": 29, "exchangeRate": 1, "installments": 1, "paymentMethod": "PIX", "originalAmount": 29, "pixInformation": {"id": "cmmqsldk302i61yruhjgqa03v", "image": "https://api.pagar.me/core/v5/transactions/tran_8dYaQGmt6WTBmOj9/qrcode?payment_method=pix", "qrCode": "00020101021226820014br.gov.bcb.pix2560pix.stone.com.br/pix/v2/3df82b8a-d2d5-46c5-955c-51bb924a0ae7520400005303986540529.005802BR5925Pagar Me Instituicao De P6014RIO DE JANEIRO62290525543dbfc567cd11a7be977b5fb6304432E", "createdAt": "2026-03-14T20:42:48.659Z", "expiresAt": null, "updatedAt": "2026-03-14T20:42:48.659Z", "endToEndId": null, "description": null, "transactionId": "cmmqslc4h02i31yru5n4k2vov"}, "originalCurrency": "BRL", "boletoInformation": null}, "subscription": null}	2026-03-14 20:42:49.566673+00
68	cmmqslc4h02i31yru5n4k2vov	TRANSACTION_PAID	F2T2Y5C	\N	{"event": "TRANSACTION_PAID", "token": "nnsgh0ys", "client": {"id": "cmmqsjsl402ho1rruuciaqkpf", "cpf": "108.755.784-46", "cnpj": null, "name": "SAVIO GEORGE SILVA DA MATA", "email": "saviogeorgee@gmail.com", "phone": "+5584994223470", "address": null}, "offerCode": "F2T2Y5C", "orderItems": [{"id": "cmmqslc2u02hx1yruyzecanah", "price": 29, "product": {"id": "cm9m6z34300h5a8hboaj3qsr8", "name": "Combo Perfeito", "externalId": null}}], "trackProps": {"ip": "187.19.254.89", "fbp": "fb.2.1773520882327.291868839601490041", "isUpsell": false, "user_agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Mobile Safari/537.36"}, "transaction": {"id": "cmmqslc4h02i31yru5n4k2vov", "amount": 29, "status": "COMPLETED", "payedAt": "2026-03-14T20:43:24.420Z", "acquirer": "Pagar.me", "currency": "BRL", "producer": {"id": "cm9lsofqx00wdfsx0shnwuqwo", "name": "Vinicius Xavier", "email": "viniciusxavierbmx2016@gmail.com", "phone": "(37) 98426-6117"}, "createdAt": "2026-03-14T20:42:46.791Z", "identifier": "app.applyfy.com.br-ORDER-cmmqslc2n02hw1yrudrampf7k", "chargeAmount": 29, "exchangeRate": 1, "installments": 1, "paymentMethod": "PIX", "originalAmount": 29, "pixInformation": {"id": "cmmqsldk302i61yruhjgqa03v", "image": "https://api.pagar.me/core/v5/transactions/tran_8dYaQGmt6WTBmOj9/qrcode?payment_method=pix", "qrCode": "00020101021226820014br.gov.bcb.pix2560pix.stone.com.br/pix/v2/3df82b8a-d2d5-46c5-955c-51bb924a0ae7520400005303986540529.005802BR5925Pagar Me Instituicao De P6014RIO DE JANEIRO62290525543dbfc567cd11a7be977b5fb6304432E", "createdAt": "2026-03-14T20:42:48.659Z", "expiresAt": null, "updatedAt": "2026-03-14T20:42:48.659Z", "endToEndId": null, "description": null, "transactionId": "cmmqslc4h02i31yru5n4k2vov"}, "originalCurrency": "BRL", "boletoInformation": null}, "subscription": null}	2026-03-14 20:43:24.762375+00
71	cmmqsqg8k02iu1yrupsel2akq	TRANSACTION_CREATED	BYBJ1VE	\N	{"event": "TRANSACTION_CREATED", "token": "nnsgh0ys", "client": {"id": "cmmqsqg3502ih1yruh82tv7nx", "cpf": "141.861.029-10", "cnpj": null, "name": "Sabrynna Ribeiro Diniz ", "email": "sabrynnadiniz2108@gmail.com", "phone": "+5547997099481", "address": {"city": "", "state": "", "number": "", "street": "", "country": "BR", "zipCode": "", "complement": "", "neighborhood": ""}}, "offerCode": "BYBJ1VE", "orderItems": [{"id": "cmmqsqg6w02ik1yrurmb1ahrm", "price": 147, "product": {"id": "cmhcc2wdj0dz914dfvc05pao2", "name": "VENDA DIRETO NO AUTOMÁTICO", "externalId": null}}], "trackProps": {"ip": "177.11.79.18", "fbc": "fb.2.1773521154501.PAZXh0bgNhZW0CMTEAc3J0YwZhcHBfaWQPNTY3MDY3MzQzMzUyNDI3AAGnCTa3nu4Jj98CNm2Dw6PZbcSIOb66JGnHg-YlK8AMgaG9gE3DpfNl5H9Bi2s_aem_TYjJxWfDYFq_cmk5j8wMng", "fbp": "fb.2.1773521159082.658402833509139416", "isUpsell": false, "user_agent": "Mozilla/5.0 (Linux; Android 15; SM-A055M Build/AP3A.240905.015.A2; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/146.0.7680.141 Mobile Safari/537.36 Instagram 420.0.0.55.74 Android (35/15; 320dpi; 720x1600; samsung; SM-A055M; a05m; mt6768; pt_BR; 903616175; IABMV/1)", "utm_medium": "bio--oti--oti_8pjmjhhttqmmqsdxzh", "utm_source": "instagram", "utm_content": "link_in_bio"}, "transaction": {"id": "cmmqsqg8k02iu1yrupsel2akq", "amount": 147, "status": "PENDING", "payedAt": null, "acquirer": "Pagar.me", "currency": "BRL", "producer": {"id": "cmga5fa0l00e445zpzpyyk4l8", "name": "Arthur Fernandes Santos", "email": "alexsandrosf3@gmail.com", "phone": "(31) 99946-1179"}, "createdAt": "2026-03-14T20:46:45.399Z", "identifier": "app.applyfy.com.br-ORDER-cmmqsqg6q02ij1yru0wvpg0xp", "chargeAmount": 147, "exchangeRate": 1, "installments": 1, "paymentMethod": "PIX", "originalAmount": 147, "pixInformation": {"id": "cmmqsqhou02iy1yruwoo5k21r", "image": "https://api.pagar.me/core/v5/transactions/tran_ZJzaqyGCRf0XnMdr/qrcode?payment_method=pix", "qrCode": "00020101021226820014br.gov.bcb.pix2560pix.stone.com.br/pix/v2/679eaae8-b675-40b7-b3ce-d76739635f065204000053039865406147.005802BR5925Pagar Me Instituicao De P6014RIO DE JANEIRO62290525098daab33737cdb708ee7b2dd6304BAFB", "createdAt": "2026-03-14T20:46:47.298Z", "expiresAt": null, "updatedAt": "2026-03-14T20:46:47.298Z", "endToEndId": null, "description": null, "transactionId": "cmmqsqg8k02iu1yrupsel2akq"}, "originalCurrency": "BRL", "boletoInformation": null}, "subscription": null}	2026-03-14 20:46:48.437821+00
72	cmmqst2er02jk1yru2l3q3z2q	TRANSACTION_CANCELED	TJJ6QUR	\N	{"event": "TRANSACTION_CANCELED", "token": "nnsgh0ys", "client": {"id": "cmmqsnuen05o01rp4wldrjgyz", "cpf": "010.835.505-51", "cnpj": null, "name": "MARIA IRISMAR ROCHA QUEIROGA", "email": "mimaqueiroga@hotmail.com.br", "phone": "+5571993567252", "address": null}, "offerCode": "TJJ6QUR", "orderItems": [{"id": "cmmqst2d802jd1yrupqe0z8c4", "price": 197, "product": {"id": "cmkgvvu5c0011lo1kqbas696j", "name": "Método AYA", "externalId": null}}, {"id": "cmmqst2d802je1yruit4vnigu", "price": 39, "product": {"id": "cmkn3cwj80si9mw1rc01wuvm3", "name": "Acesso Vitalício", "externalId": null}}, {"id": "cmmqst2d802jf1yru5fawksfb", "price": 59, "product": {"id": "cmkn3qis8003p1rp1mff8j4r3", "name": "Grupo de Vídeos Virais (Decola Achadinhos)", "externalId": null}}], "trackProps": {"ip": "181.77.48.20", "fbp": "fb.2.1773521066431.13576008143697581", "isUpsell": false, "user_agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Mobile Safari/537.36"}, "transaction": {"id": "cmmqst2er02jk1yru2l3q3z2q", "amount": 295, "status": "FAILED", "payedAt": null, "acquirer": "Pagar.me", "currency": "BRL", "producer": {"id": "cmkfg73gj07mkqh1kavr5ba0l", "name": "Lorena Curtarelli Machado Nomelini", "email": "lo_cmachado@yahoo.com.br", "phone": "(16) 99709-1381"}, "createdAt": "2026-03-14T20:48:47.447Z", "identifier": "app.applyfy.com.br-ORDER-cmmqst2cx02jc1yru2708780w", "chargeAmount": 377.29, "exchangeRate": 1, "installments": 12, "paymentMethod": "CREDIT_CARD", "originalAmount": 295, "pixInformation": null, "originalCurrency": "BRL", "boletoInformation": null}, "subscription": null}	2026-03-14 20:48:51.216912+00
81	cmmqt0rp305q31rp4vgxzt5fm	TRANSACTION_CREATED	M8URQ2E	\N	{"event": "TRANSACTION_CREATED", "token": "nnsgh0ys", "client": {"id": "cmmqsym1302j81rruaxbh6u64", "cpf": "008.152.544-31", "cnpj": null, "name": "Jorge André Dantas De Oliveira ", "email": "jorgeandre642@gmail.com", "phone": "+5521994448080", "address": null}, "offerCode": "M8URQ2E", "orderItems": [{"id": "cmmqt0rob05q11rp4v974wd2m", "price": 297, "product": {"id": "cmmcuipbl01ps1ro9si7fekp6", "name": "TikTok Hub Pro", "externalId": null}}], "trackProps": {"ip": "187.19.245.218", "isUpsell": false, "user_agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 18_7 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/26.3 Mobile/15E148 Safari/604.1", "affiliate_code": "ukjulh1"}, "transaction": {"id": "cmmqt0rp305q31rp4vgxzt5fm", "amount": 282.15, "status": "PENDING", "payedAt": null, "acquirer": "Pagar.me", "currency": "BRL", "producer": {"id": "cmm188erv078y1ypt5kdv8cok", "name": "Lucas Rodrigues de Souza", "email": "lucasrdsouza1@gmail.com", "phone": "(55) 99727-9692"}, "createdAt": "2026-03-14T20:54:46.835Z", "identifier": "app.applyfy.com.br-ORDER-cmmqt0ro305q01rp48z6o36ku", "chargeAmount": 282.15, "exchangeRate": 1, "installments": 1, "paymentMethod": "PIX", "originalAmount": 282.15, "pixInformation": {"id": "cmmqt0tkl05qc1rp4k56q2ao4", "image": "https://api.pagar.me/core/v5/transactions/tran_8B2JNbhG5hdDJNWb/qrcode?payment_method=pix", "qrCode": "00020101021226820014br.gov.bcb.pix2560pix.stone.com.br/pix/v2/e49cceb0-5cdb-44e8-b9a9-f95be73a9d0f5204000053039865406282.155802BR5925Pagar Me Instituicao De P6014RIO DE JANEIRO6229052561a89ee3659ff8ec69fb25be3630474EE", "createdAt": "2026-03-14T20:54:49.254Z", "expiresAt": null, "updatedAt": "2026-03-14T20:54:49.254Z", "endToEndId": null, "description": null, "transactionId": "cmmqt0rp305q31rp4vgxzt5fm"}, "originalCurrency": "BRL", "boletoInformation": null}, "subscription": null}	2026-03-14 20:54:50.189471+00
82	cmmqt17j805m81yp4mokuqzza	TRANSACTION_CREATED	P75L8Q8	\N	{"event": "TRANSACTION_CREATED", "token": "nnsgh0ys", "client": {"id": "cmmqt08g005pl1rp4sjtsc3t4", "cpf": "090.391.279-13", "cnpj": null, "name": "Thaís França ", "email": "ta.ty-156@hotmail.com", "phone": "+5541988676422", "address": null}, "offerCode": "P75L8Q8", "orderItems": [{"id": "cmmqt17hz05m21yp43e6xuvat", "price": 34, "product": {"id": "cmg80wou103t659i3p55lu35d", "name": "LUCRANDO COM A SHÔ", "externalId": null}}], "trackProps": {"ip": "179.68.110.180", "fbc": "fb.2.1773521640679.PAZXh0bgNhZW0CMTAAc3J0YwZhcHBfaWQPMTI0MDI0NTc0Mjg3NDE0AAGnjPUdtZ3OnIXLQJ_up8r8sZQQgJDyAfA2jbSwfS1TBTilapccOqNzAVBOLfQ_aem_pgVSo6eS_4GPqLnE-n3QXg", "fbp": "fb.2.1773521640671.134449745859330178", "isUpsell": false, "user_agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 18_7 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/23D8133 Instagram 419.0.0.27.74 (iPhone18,2; iOS 26_3_1; pt_BR; pt; scale=3.00; 1320x2868; IABMV/1; 895010607) Safari/604.1"}, "transaction": {"id": "cmmqt17j805m81yp4mokuqzza", "amount": 34, "status": "PENDING", "payedAt": null, "acquirer": "Pagar.me", "currency": "BRL", "producer": {"id": "cmccde86a0ek8ikxtoaw52r76", "name": "Júlia Pereira Cardozo ", "email": "juliacardozomkt@gmail.com", "phone": "(51) 98947-0504"}, "createdAt": "2026-03-14T20:55:07.341Z", "identifier": "app.applyfy.com.br-ORDER-cmmqt17ht05m11yp4l2fg4v9e", "chargeAmount": 34, "exchangeRate": 1, "installments": 1, "paymentMethod": "PIX", "originalAmount": 34, "pixInformation": {"id": "cmmqt191705mc1yp49urdtksu", "image": "https://api.pagar.me/core/v5/transactions/tran_nGwkbDQc3HeYApPo/qrcode?payment_method=pix", "qrCode": "00020101021226820014br.gov.bcb.pix2560pix.stone.com.br/pix/v2/1ef067bb-46a4-4958-9cec-bddf471a12a0520400005303986540534.005802BR5925Pagar Me Instituicao De P6014RIO DE JANEIRO6229052506e96b5db8890ecb0b25ddf046304A026", "createdAt": "2026-03-14T20:55:09.284Z", "expiresAt": null, "updatedAt": "2026-03-14T20:55:09.284Z", "endToEndId": null, "description": null, "transactionId": "cmmqt17j805m81yp4mokuqzza"}, "originalCurrency": "BRL", "boletoInformation": null}, "subscription": null}	2026-03-14 20:55:10.178067+00
83	cmmqt1p2900971rpduuqaiklx	PRODUCER_CREATED	\N	cmmqt1p2900971rpduuqaiklx	{"event": "PRODUCER_CREATED", "token": "nnsgh0ys", "producer": {"id": "cmmqt1p2900971rpduuqaiklx", "name": "Patricia Rolemberg", "email": "rolembergp1@gmail.com", "phone": "(21) 96645-0690", "status": "WAITING_FOR_EMAIL_VERIFICATION", "document": null, "createdAt": "2026-03-14T20:55:30.081Z"}}	2026-03-14 20:55:31.042131+00
85	cmmqt17j805m81yp4mokuqzza	TRANSACTION_PAID	P75L8Q8	\N	{"event": "TRANSACTION_PAID", "token": "nnsgh0ys", "client": {"id": "cmmqt08g005pl1rp4sjtsc3t4", "cpf": "090.391.279-13", "cnpj": null, "name": "Thaís França ", "email": "ta.ty-156@hotmail.com", "phone": "+5541988676422", "address": null}, "offerCode": "P75L8Q8", "orderItems": [{"id": "cmmqt17hz05m21yp43e6xuvat", "price": 34, "product": {"id": "cmg80wou103t659i3p55lu35d", "name": "LUCRANDO COM A SHÔ", "externalId": null}}], "trackProps": {"ip": "179.68.110.180", "fbc": "fb.2.1773521640679.PAZXh0bgNhZW0CMTAAc3J0YwZhcHBfaWQPMTI0MDI0NTc0Mjg3NDE0AAGnjPUdtZ3OnIXLQJ_up8r8sZQQgJDyAfA2jbSwfS1TBTilapccOqNzAVBOLfQ_aem_pgVSo6eS_4GPqLnE-n3QXg", "fbp": "fb.2.1773521640671.134449745859330178", "isUpsell": false, "user_agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 18_7 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/23D8133 Instagram 419.0.0.27.74 (iPhone18,2; iOS 26_3_1; pt_BR; pt; scale=3.00; 1320x2868; IABMV/1; 895010607) Safari/604.1"}, "transaction": {"id": "cmmqt17j805m81yp4mokuqzza", "amount": 34, "status": "COMPLETED", "payedAt": "2026-03-14T20:55:45.512Z", "acquirer": "Pagar.me", "currency": "BRL", "producer": {"id": "cmccde86a0ek8ikxtoaw52r76", "name": "Júlia Pereira Cardozo ", "email": "juliacardozomkt@gmail.com", "phone": "(51) 98947-0504"}, "createdAt": "2026-03-14T20:55:07.341Z", "identifier": "app.applyfy.com.br-ORDER-cmmqt17ht05m11yp4l2fg4v9e", "chargeAmount": 34, "exchangeRate": 1, "installments": 1, "paymentMethod": "PIX", "originalAmount": 34, "pixInformation": {"id": "cmmqt191705mc1yp49urdtksu", "image": "https://api.pagar.me/core/v5/transactions/tran_nGwkbDQc3HeYApPo/qrcode?payment_method=pix", "qrCode": "00020101021226820014br.gov.bcb.pix2560pix.stone.com.br/pix/v2/1ef067bb-46a4-4958-9cec-bddf471a12a0520400005303986540534.005802BR5925Pagar Me Instituicao De P6014RIO DE JANEIRO6229052506e96b5db8890ecb0b25ddf046304A026", "createdAt": "2026-03-14T20:55:09.284Z", "expiresAt": null, "updatedAt": "2026-03-14T20:55:09.284Z", "endToEndId": null, "description": null, "transactionId": "cmmqt17j805m81yp4mokuqzza"}, "originalCurrency": "BRL", "boletoInformation": null}, "subscription": null}	2026-03-14 20:55:46.074841+00
86	cmmqt0rp305q31rp4vgxzt5fm	TRANSACTION_PAID	M8URQ2E	\N	{"event": "TRANSACTION_PAID", "split": {"commissions": [{"type": "product-owner", "amount": 58.19, "producerId": "cmm188erv078y1ypt5kdv8cok", "splitAccount": {"id": "cmm29yeok057t1kqvr3gp3w7d", "status": "APPROVED", "acquirer": "pagar_me", "currency": "BRL", "createdAt": "2026-02-25T16:54:35.732Z", "updatedAt": "2026-02-25T19:49:54.387Z", "customData": {}, "externalId": "re_cmm29yeyu4uxf0k9tx7enr3pn", "producerId": "cmm188erv078y1ypt5kdv8cok", "transfered": 0, "errorMessage": null, "waitingFunds": 0, "availableBalance": 0}}, {"type": "affiliate", "amount": 144.18, "producerId": "cmmpagjbm01y71smm8f8l295m", "splitAccount": {"id": "cmmpblull04jx1ypfy686fzbd", "status": "APPROVED", "acquirer": "pagar_me", "currency": "BRL", "createdAt": "2026-03-13T19:59:31.113Z", "updatedAt": "2026-03-13T20:09:09.365Z", "customData": {"errorMessage": null}, "externalId": "re_cmmpbluy9vtq30l9ts0c0cul9", "producerId": "cmmpagjbm01y71smm8f8l295m", "transfered": 0, "errorMessage": null, "waitingFunds": 0, "availableBalance": 0}}, {"type": "affiliate", "amount": 58.98, "producerId": "cmly98fo4085l1qqehy5as0fz", "splitAccount": {"id": "cmm3jk2vb00ai1rqqdlae77pr", "status": "APPROVED", "acquirer": "pagar_me", "currency": "BRL", "createdAt": "2026-02-26T14:11:09.575Z", "updatedAt": "2026-02-26T18:19:36.402Z", "customData": {"errorMessage": null}, "externalId": "re_cmm3jk3f6abk90l9ttfru55gv", "producerId": "cmly98fo4085l1qqehy5as0fz", "transfered": 0, "errorMessage": null, "waitingFunds": 0, "availableBalance": 0}}], "totalOwnerFee": 20.8}, "token": "nnsgh0ys", "client": {"id": "cmmqsym1302j81rruaxbh6u64", "cpf": "008.152.544-31", "cnpj": null, "name": "Jorge André Dantas De Oliveira ", "email": "jorgeandre642@gmail.com", "phone": "+5521994448080", "address": null}, "offerCode": "M8URQ2E", "orderItems": [{"id": "cmmqt0rob05q11rp4v974wd2m", "price": 297, "product": {"id": "cmmcuipbl01ps1ro9si7fekp6", "name": "TikTok Hub Pro", "externalId": null}}], "trackProps": {"ip": "187.19.245.218", "isUpsell": false, "user_agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 18_7 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/26.3 Mobile/15E148 Safari/604.1", "affiliate_code": "ukjulh1"}, "transaction": {"id": "cmmqt0rp305q31rp4vgxzt5fm", "amount": 282.15, "status": "COMPLETED", "payedAt": "2026-03-14T20:55:59.001Z", "acquirer": "Pagar.me", "currency": "BRL", "producer": {"id": "cmm188erv078y1ypt5kdv8cok", "name": "Lucas Rodrigues de Souza", "email": "lucasrdsouza1@gmail.com", "phone": "(55) 99727-9692"}, "createdAt": "2026-03-14T20:54:46.835Z", "identifier": "app.applyfy.com.br-ORDER-cmmqt0ro305q01rp48z6o36ku", "chargeAmount": 282.15, "exchangeRate": 1, "installments": 1, "paymentMethod": "PIX", "originalAmount": 282.15, "pixInformation": {"id": "cmmqt0tkl05qc1rp4k56q2ao4", "image": "https://api.pagar.me/core/v5/transactions/tran_8B2JNbhG5hdDJNWb/qrcode?payment_method=pix", "qrCode": "00020101021226820014br.gov.bcb.pix2560pix.stone.com.br/pix/v2/e49cceb0-5cdb-44e8-b9a9-f95be73a9d0f5204000053039865406282.155802BR5925Pagar Me Instituicao De P6014RIO DE JANEIRO6229052561a89ee3659ff8ec69fb25be3630474EE", "createdAt": "2026-03-14T20:54:49.254Z", "expiresAt": null, "updatedAt": "2026-03-14T20:54:49.254Z", "endToEndId": null, "description": null, "transactionId": "cmmqt0rp305q31rp4vgxzt5fm"}, "originalCurrency": "BRL", "boletoInformation": null}, "subscription": null}	2026-03-14 20:55:59.322041+00
97	tx-TRANSFER_CREATED-	TRANSFER_CREATED	\N	\N	{"event": "TRANSFER_CREATED", "sents": [], "token": "nnsgh0ys", "withdraw": {"id": "cmmqtdq591td81zqqv2u39wlb", "amount": 363.33, "status": "PENDING", "message": null, "currency": "BRL", "producer": {"id": "cmdomywys009lxfvof3wbykp7", "name": "Pedro Henrique Carneiro Frade", "email": "pedrofrade@outlook.com", "phone": "(11) 91740-8090"}, "createdAt": "2026-03-14T21:04:51.356Z", "feeAmount": 3.67, "updatedAt": "2026-03-14T21:04:51.356Z", "receivedAmount": 0, "clientIdentifier": null}, "payoutAccount": {"id": "cmkv2j0t50ki71zmwr5ohoivr", "pix": "(11) 91740-8090", "bank": "077", "agency": "0001", "status": "ACTIVE", "account": "8134267", "pixType": "phone", "createdAt": "2026-01-26T11:12:35.033Z", "deletedAt": null, "ownerName": "PEDRO HENRIQUE CARNEIRO FRADE", "updatedAt": "2026-01-26T11:12:45.423Z", "accountType": "CHECKING", "agencyDigit": "", "accountDigit": "5", "cryptoAddress": "", "cryptoNetwork": null, "ownerDocument": "26.031.452/0001-24"}}	2026-03-14 21:04:54.618526+00
104	cmmqtkta302nx1rru8aqvizu1	TRANSACTION_CREATED	H0TXXY5	\N	{"event": "TRANSACTION_CREATED", "token": "nnsgh0ys", "client": {"id": "cmmqtkt3c02ni1rrutqry8u6a", "cpf": "420.333.338-50", "cnpj": null, "name": "Nicoly Ingrid do Nascimento Teixeira ", "email": "nicolyteixeira2011@gmail.com", "phone": "+5511934999729", "address": {"city": "", "state": "", "number": "", "street": "", "country": "BR", "zipCode": "", "complement": "", "neighborhood": ""}}, "offerCode": "H0TXXY5", "orderItems": [{"id": "cmmqtkt8802nl1rrus2zia5nh", "price": 14.9, "product": {"id": "cmm9lkvhh01eg1yruk8acisyk", "name": "Cativantes Cardapio", "externalId": null}}], "trackProps": {"ip": "160.20.182.106", "fbc": "fb.2.1773522510825.PAZXh0bgNhZW0BMABhZGlkAaswV5uttVZzcnRjBmFwcF9pZA8xMjQwMjQ1NzQyODc0MTQAAadqQ3MLh3Oi_ewr_suXwT-5UXyatJZUub30DHLGKFaV8oyt6dGBtCPLoadA2g_aem_L-U0_-hYu3kh5fHODlq4pA", "fbp": "fb.2.1773522510826.202667748278663228", "utm_id": "120242800769330742", "isUpsell": false, "utm_term": "CONJUNTO+09", "user_agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 18_7 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/23D8133 Instagram 419.0.0.27.74 (iPhone16,1; iOS 26_3_1; pt_BR; pt; scale=3.00; 1179x2556; IABMV/1; 895010607) Safari/604.1", "utm_medium": "Instagram_Stories", "utm_source": "ig", "utm_content": "CRIATIVO+01", "utm_campaign": "[ABO]+CARDAPIO+1-1-1-+[04-03]"}, "transaction": {"id": "cmmqtkta302nx1rru8aqvizu1", "amount": 14.9, "status": "PENDING", "payedAt": null, "acquirer": "Pagar.me", "currency": "BRL", "producer": {"id": "cmm9irpi500i51rpbx5z05nll", "name": "Talita Lorraine de Lima Mendes", "email": "talitalorraine2002@gmail.com", "phone": "(31) 99559-8475"}, "createdAt": "2026-03-14T21:10:21.984Z", "identifier": "app.applyfy.com.br-ORDER-cmmqtkt7l02nk1rrub2mh97uw", "chargeAmount": 14.9, "exchangeRate": 1, "installments": 1, "paymentMethod": "CREDIT_CARD", "originalAmount": 14.9, "pixInformation": null, "originalCurrency": "BRL", "boletoInformation": null}, "subscription": null}	2026-03-14 21:10:28.919304+00
105	cmmqtkta302nx1rru8aqvizu1	TRANSACTION_CANCELED	H0TXXY5	\N	{"event": "TRANSACTION_CANCELED", "token": "nnsgh0ys", "client": {"id": "cmmqtkt3c02ni1rrutqry8u6a", "cpf": "420.333.338-50", "cnpj": null, "name": "Nicoly Ingrid do Nascimento Teixeira ", "email": "nicolyteixeira2011@gmail.com", "phone": "+5511934999729", "address": {"city": "", "state": "", "number": "", "street": "", "country": "BR", "zipCode": "", "complement": "", "neighborhood": ""}}, "offerCode": "H0TXXY5", "orderItems": [{"id": "cmmqtkt8802nl1rrus2zia5nh", "price": 14.9, "product": {"id": "cmm9lkvhh01eg1yruk8acisyk", "name": "Cativantes Cardapio", "externalId": null}}], "trackProps": {"ip": "160.20.182.106", "fbc": "fb.2.1773522510825.PAZXh0bgNhZW0BMABhZGlkAaswV5uttVZzcnRjBmFwcF9pZA8xMjQwMjQ1NzQyODc0MTQAAadqQ3MLh3Oi_ewr_suXwT-5UXyatJZUub30DHLGKFaV8oyt6dGBtCPLoadA2g_aem_L-U0_-hYu3kh5fHODlq4pA", "fbp": "fb.2.1773522510826.202667748278663228", "utm_id": "120242800769330742", "isUpsell": false, "utm_term": "CONJUNTO+09", "user_agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 18_7 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/23D8133 Instagram 419.0.0.27.74 (iPhone16,1; iOS 26_3_1; pt_BR; pt; scale=3.00; 1179x2556; IABMV/1; 895010607) Safari/604.1", "utm_medium": "Instagram_Stories", "utm_source": "ig", "utm_content": "CRIATIVO+01", "utm_campaign": "[ABO]+CARDAPIO+1-1-1-+[04-03]"}, "transaction": {"id": "cmmqtkta302nx1rru8aqvizu1", "amount": 14.9, "status": "FAILED", "payedAt": null, "acquirer": "Pagar.me", "currency": "BRL", "producer": {"id": "cmm9irpi500i51rpbx5z05nll", "name": "Talita Lorraine de Lima Mendes", "email": "talitalorraine2002@gmail.com", "phone": "(31) 99559-8475"}, "createdAt": "2026-03-14T21:10:21.984Z", "identifier": "app.applyfy.com.br-ORDER-cmmqtkt7l02nk1rrub2mh97uw", "chargeAmount": 14.9, "exchangeRate": 1, "installments": 1, "paymentMethod": "CREDIT_CARD", "originalAmount": 14.9, "pixInformation": null, "originalCurrency": "BRL", "boletoInformation": null}, "subscription": null}	2026-03-14 21:10:39.165651+00
108	cmmqtm32z05sh1rp4duby5goz	TRANSACTION_CREATED	H0TXXY5	\N	{"event": "TRANSACTION_CREATED", "token": "nnsgh0ys", "client": {"id": "cmmqtkt3c02ni1rrutqry8u6a", "cpf": "420.333.338-50", "cnpj": null, "name": "Nicoly Ingrid do Nascimento Teixeira ", "email": "nicolyteixeira2011@gmail.com", "phone": "+5511934999729", "address": {"city": "", "state": "", "number": "", "street": "", "country": "BR", "zipCode": "", "complement": "", "neighborhood": ""}}, "offerCode": "H0TXXY5", "orderItems": [{"id": "cmmqtm32605s51rp4qh2a423s", "price": 14.9, "product": {"id": "cmm9lkvhh01eg1yruk8acisyk", "name": "Cativantes Cardapio", "externalId": null}}], "trackProps": {"ip": "160.20.182.106", "fbc": "fb.2.1773522510825.PAZXh0bgNhZW0BMABhZGlkAaswV5uttVZzcnRjBmFwcF9pZA8xMjQwMjQ1NzQyODc0MTQAAadqQ3MLh3Oi_ewr_suXwT-5UXyatJZUub30DHLGKFaV8oyt6dGBtCPLoadA2g_aem_L-U0_-hYu3kh5fHODlq4pA", "fbp": "fb.2.1773522510826.202667748278663228", "utm_id": "120242800769330742", "isUpsell": false, "utm_term": "CONJUNTO+09", "user_agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 18_7 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/23D8133 Instagram 419.0.0.27.74 (iPhone16,1; iOS 26_3_1; pt_BR; pt; scale=3.00; 1179x2556; IABMV/1; 895010607) Safari/604.1", "utm_medium": "Instagram_Stories", "utm_source": "ig", "utm_content": "CRIATIVO+01", "utm_campaign": "[ABO]+CARDAPIO+1-1-1-+[04-03]"}, "transaction": {"id": "cmmqtm32z05sh1rp4duby5goz", "amount": 14.9, "status": "PENDING", "payedAt": null, "acquirer": "Pagar.me", "currency": "BRL", "producer": {"id": "cmm9irpi500i51rpbx5z05nll", "name": "Talita Lorraine de Lima Mendes", "email": "talitalorraine2002@gmail.com", "phone": "(31) 99559-8475"}, "createdAt": "2026-03-14T21:11:21.367Z", "identifier": "app.applyfy.com.br-ORDER-cmmqtm32005s41rp416nms00w", "chargeAmount": 14.9, "exchangeRate": 1, "installments": 1, "paymentMethod": "PIX", "originalAmount": 14.9, "pixInformation": {"id": "cmmqtm4d405sl1rp4o65qx04h", "image": "https://api.pagar.me/core/v5/transactions/tran_V0Em5pNi7HrywWg8/qrcode?payment_method=pix", "qrCode": "00020101021226820014br.gov.bcb.pix2560pix.stone.com.br/pix/v2/7e8882b2-eb48-4616-ab9b-02b7cda59894520400005303986540514.905802BR5925Pagar Me Instituicao De P6014RIO DE JANEIRO622905257f987b4a5148cbdca46055da76304EA15", "createdAt": "2026-03-14T21:11:23.011Z", "expiresAt": null, "updatedAt": "2026-03-14T21:11:23.011Z", "endToEndId": null, "description": null, "transactionId": "cmmqtm32z05sh1rp4duby5goz"}, "originalCurrency": "BRL", "boletoInformation": null}, "subscription": null}	2026-03-14 21:11:24.392335+00
109	cmmqtm32z05sh1rp4duby5goz	TRANSACTION_PAID	H0TXXY5	\N	{"event": "TRANSACTION_PAID", "token": "nnsgh0ys", "client": {"id": "cmmqtkt3c02ni1rrutqry8u6a", "cpf": "420.333.338-50", "cnpj": null, "name": "Nicoly Ingrid do Nascimento Teixeira ", "email": "nicolyteixeira2011@gmail.com", "phone": "+5511934999729", "address": {"city": "", "state": "", "number": "", "street": "", "country": "BR", "zipCode": "", "complement": "", "neighborhood": ""}}, "offerCode": "H0TXXY5", "orderItems": [{"id": "cmmqtm32605s51rp4qh2a423s", "price": 14.9, "product": {"id": "cmm9lkvhh01eg1yruk8acisyk", "name": "Cativantes Cardapio", "externalId": null}}], "trackProps": {"ip": "160.20.182.106", "fbc": "fb.2.1773522510825.PAZXh0bgNhZW0BMABhZGlkAaswV5uttVZzcnRjBmFwcF9pZA8xMjQwMjQ1NzQyODc0MTQAAadqQ3MLh3Oi_ewr_suXwT-5UXyatJZUub30DHLGKFaV8oyt6dGBtCPLoadA2g_aem_L-U0_-hYu3kh5fHODlq4pA", "fbp": "fb.2.1773522510826.202667748278663228", "utm_id": "120242800769330742", "isUpsell": false, "utm_term": "CONJUNTO+09", "user_agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 18_7 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/23D8133 Instagram 419.0.0.27.74 (iPhone16,1; iOS 26_3_1; pt_BR; pt; scale=3.00; 1179x2556; IABMV/1; 895010607) Safari/604.1", "utm_medium": "Instagram_Stories", "utm_source": "ig", "utm_content": "CRIATIVO+01", "utm_campaign": "[ABO]+CARDAPIO+1-1-1-+[04-03]"}, "transaction": {"id": "cmmqtm32z05sh1rp4duby5goz", "amount": 14.9, "status": "COMPLETED", "payedAt": "2026-03-14T21:12:04.613Z", "acquirer": "Pagar.me", "currency": "BRL", "producer": {"id": "cmm9irpi500i51rpbx5z05nll", "name": "Talita Lorraine de Lima Mendes", "email": "talitalorraine2002@gmail.com", "phone": "(31) 99559-8475"}, "createdAt": "2026-03-14T21:11:21.367Z", "identifier": "app.applyfy.com.br-ORDER-cmmqtm32005s41rp416nms00w", "chargeAmount": 14.9, "exchangeRate": 1, "installments": 1, "paymentMethod": "PIX", "originalAmount": 14.9, "pixInformation": {"id": "cmmqtm4d405sl1rp4o65qx04h", "image": "https://api.pagar.me/core/v5/transactions/tran_V0Em5pNi7HrywWg8/qrcode?payment_method=pix", "qrCode": "00020101021226820014br.gov.bcb.pix2560pix.stone.com.br/pix/v2/7e8882b2-eb48-4616-ab9b-02b7cda59894520400005303986540514.905802BR5925Pagar Me Instituicao De P6014RIO DE JANEIRO622905257f987b4a5148cbdca46055da76304EA15", "createdAt": "2026-03-14T21:11:23.011Z", "expiresAt": null, "updatedAt": "2026-03-14T21:11:23.011Z", "endToEndId": null, "description": null, "transactionId": "cmmqtm32z05sh1rp4duby5goz"}, "originalCurrency": "BRL", "boletoInformation": null}, "subscription": null}	2026-03-14 21:12:05.295315+00
117	cmmqu3gwj00ii1rpddf0zpk20	PRODUCER_CREATED	\N	cmmqu3gwj00ii1rpddf0zpk20	{"event": "PRODUCER_CREATED", "token": "nnsgh0ys", "producer": {"id": "cmmqu3gwj00ii1rpddf0zpk20", "name": "Fabia Aparecida Martins Soares", "email": "fabia019@icloud.com", "phone": "(38) 99802-9788", "status": "WAITING_FOR_EMAIL_VERIFICATION", "document": null, "createdAt": "2026-03-14T21:24:52.435Z"}}	2026-03-14 21:24:53.620859+00
121	cmmqu8fr102op1rru4hrhm2kd	TRANSACTION_CREATED	H0TXXY5	\N	{"event": "TRANSACTION_CREATED", "token": "nnsgh0ys", "client": {"id": "cmmqu61sz02og1rrux9321f0a", "cpf": "127.868.177-90", "cnpj": null, "name": "geisa dos", "email": "geisa2mc@gmail.com", "phone": "+5527996441469", "address": null}, "offerCode": "H0TXXY5", "orderItems": [{"id": "cmmqu8fpu02ok1rru3w2zubr1", "price": 14.9, "product": {"id": "cmm9lkvhh01eg1yruk8acisyk", "name": "Cativantes Cardapio", "externalId": null}}], "trackProps": {"ip": "179.102.141.42", "fbp": "fb.2.1773523541089.80768118067154639", "isUpsell": false, "user_agent": "Mozilla/5.0 (Linux; Android 15; 2412DPC0AG Build/AP3A.240905.015.A2; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/145.0.7632.159 Mobile Safari/537.36 Instagram 420.0.0.55.74 Android (35/15; 520dpi; 1220x2712; Xiaomi/POCO; 2412DPC0AG; rodin; mt6899; pt_BR; 903616139; IABMV/1)"}, "transaction": {"id": "cmmqu8fr102op1rru4hrhm2kd", "amount": 14.9, "status": "PENDING", "payedAt": null, "acquirer": "Pagar.me", "currency": "BRL", "producer": {"id": "cmm9irpi500i51rpbx5z05nll", "name": "Talita Lorraine de Lima Mendes", "email": "talitalorraine2002@gmail.com", "phone": "(31) 99559-8475"}, "createdAt": "2026-03-14T21:28:44.199Z", "identifier": "app.applyfy.com.br-ORDER-cmmqu8fpo02oj1rrus10ti9ia", "chargeAmount": 14.9, "exchangeRate": 1, "installments": 1, "paymentMethod": "PIX", "originalAmount": 14.9, "pixInformation": {"id": "cmmqu8h8602ot1rrutdzvvz01", "image": "https://api.pagar.me/core/v5/transactions/tran_Zd0x23svYF7AK8br/qrcode?payment_method=pix", "qrCode": "00020101021226820014br.gov.bcb.pix2560pix.stone.com.br/pix/v2/7686333a-f224-4a35-8003-bc81dfc165f1520400005303986540514.905802BR5925Pagar Me Instituicao De P6014RIO DE JANEIRO622905252110108ee5f35cffc6958fd656304A815", "createdAt": "2026-03-14T21:28:46.117Z", "expiresAt": null, "updatedAt": "2026-03-14T21:28:46.117Z", "endToEndId": null, "description": null, "transactionId": "cmmqu8fr102op1rru4hrhm2kd"}, "originalCurrency": "BRL", "boletoInformation": null}, "subscription": null}	2026-03-14 21:28:47.973918+00
122	cmmqu8fr102op1rru4hrhm2kd	TRANSACTION_PAID	H0TXXY5	\N	{"event": "TRANSACTION_PAID", "token": "nnsgh0ys", "client": {"id": "cmmqu61sz02og1rrux9321f0a", "cpf": "127.868.177-90", "cnpj": null, "name": "geisa dos", "email": "geisa2mc@gmail.com", "phone": "+5527996441469", "address": null}, "offerCode": "H0TXXY5", "orderItems": [{"id": "cmmqu8fpu02ok1rru3w2zubr1", "price": 14.9, "product": {"id": "cmm9lkvhh01eg1yruk8acisyk", "name": "Cativantes Cardapio", "externalId": null}}], "trackProps": {"ip": "179.102.141.42", "fbp": "fb.2.1773523541089.80768118067154639", "isUpsell": false, "user_agent": "Mozilla/5.0 (Linux; Android 15; 2412DPC0AG Build/AP3A.240905.015.A2; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/145.0.7632.159 Mobile Safari/537.36 Instagram 420.0.0.55.74 Android (35/15; 520dpi; 1220x2712; Xiaomi/POCO; 2412DPC0AG; rodin; mt6899; pt_BR; 903616139; IABMV/1)"}, "transaction": {"id": "cmmqu8fr102op1rru4hrhm2kd", "amount": 14.9, "status": "COMPLETED", "payedAt": "2026-03-14T21:29:25.945Z", "acquirer": "Pagar.me", "currency": "BRL", "producer": {"id": "cmm9irpi500i51rpbx5z05nll", "name": "Talita Lorraine de Lima Mendes", "email": "talitalorraine2002@gmail.com", "phone": "(31) 99559-8475"}, "createdAt": "2026-03-14T21:28:44.199Z", "identifier": "app.applyfy.com.br-ORDER-cmmqu8fpo02oj1rrus10ti9ia", "chargeAmount": 14.9, "exchangeRate": 1, "installments": 1, "paymentMethod": "PIX", "originalAmount": 14.9, "pixInformation": {"id": "cmmqu8h8602ot1rrutdzvvz01", "image": "https://api.pagar.me/core/v5/transactions/tran_Zd0x23svYF7AK8br/qrcode?payment_method=pix", "qrCode": "00020101021226820014br.gov.bcb.pix2560pix.stone.com.br/pix/v2/7686333a-f224-4a35-8003-bc81dfc165f1520400005303986540514.905802BR5925Pagar Me Instituicao De P6014RIO DE JANEIRO622905252110108ee5f35cffc6958fd656304A815", "createdAt": "2026-03-14T21:28:46.117Z", "expiresAt": null, "updatedAt": "2026-03-14T21:28:46.117Z", "endToEndId": null, "description": null, "transactionId": "cmmqu8fr102op1rru4hrhm2kd"}, "originalCurrency": "BRL", "boletoInformation": null}, "subscription": null}	2026-03-14 21:29:27.329078+00
128	cmmqudz8205qx1yp417765etw	TRANSACTION_CREATED	2HKSXMF	\N	{"event": "TRANSACTION_CREATED", "token": "nnsgh0ys", "client": {"id": "cmmqucoib02oe1yruo7w2dgbd", "cpf": "215.686.077-76", "cnpj": null, "name": "Wellington Leandro de castro blois", "email": "wellingtonleandro755@gmail.com", "phone": "+5521966967919", "address": null}, "offerCode": "2HKSXMF", "orderItems": [{"id": "cmmqudz5705qq1yp4yz4e7sfw", "price": 97, "product": {"id": "cmgacfywz02l0jiq7w4etqdvi", "name": "Mentoria Junção Milionária", "externalId": null}}, {"id": "cmmqudz5705qr1yp401c51i80", "price": 39.9, "product": {"id": "cmgaczjz501nxlfkzsdrewdfv", "name": "ACESSO VITALÍCIO", "externalId": null}}], "trackProps": {"ip": "200.150.246.6", "isUpsell": false, "user_agent": "Mozilla/5.0 (Linux; Android 14; moto g14 Build/UTLBS34.102-91-3) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/145.0.7632.159 Mobile Safari/537.36", "affiliate_code": "h7xrif5"}, "transaction": {"id": "cmmqudz8205qx1yp417765etw", "amount": 136.9, "status": "PENDING", "payedAt": null, "acquirer": "Pagar.me", "currency": "BRL", "producer": {"id": "cmga5fa0l00e445zpzpyyk4l8", "name": "Arthur Fernandes Santos", "email": "alexsandrosf3@gmail.com", "phone": "(31) 99946-1179"}, "createdAt": "2026-03-14T21:33:02.681Z", "identifier": "app.applyfy.com.br-ORDER-cmmqudz4l05qp1yp4sxigcmga", "chargeAmount": 136.9, "exchangeRate": 1, "installments": 1, "paymentMethod": "PIX", "originalAmount": 136.9, "pixInformation": {"id": "cmmque1q605r21yp456oh1n4s", "image": "https://api.pagar.me/core/v5/transactions/tran_MYGLyb3zf6imQBKe/qrcode?payment_method=pix", "qrCode": "00020101021226820014br.gov.bcb.pix2560pix.stone.com.br/pix/v2/55ff069c-8718-415c-af87-927853ae5cac5204000053039865406136.905802BR5925Pagar Me Instituicao De P6014RIO DE JANEIRO62290525ffe6a6c4918e0b69a55ced2c763045DE3", "createdAt": "2026-03-14T21:33:05.970Z", "expiresAt": null, "updatedAt": "2026-03-14T21:33:05.970Z", "endToEndId": null, "description": null, "transactionId": "cmmqudz8205qx1yp417765etw"}, "originalCurrency": "BRL", "boletoInformation": null}, "subscription": null}	2026-03-14 21:33:07.647122+00
131	cmmqug0fw02pf1rrumchk0t8c	TRANSACTION_CREATED	2HKSXMF	\N	{"event": "TRANSACTION_CREATED", "token": "nnsgh0ys", "client": {"id": "cmmqucoib02oe1yruo7w2dgbd", "cpf": "215.686.077-76", "cnpj": null, "name": "Wellington Leandro de castro blois", "email": "wellingtonleandro755@gmail.com", "phone": "+5521966967919", "address": null}, "offerCode": "2HKSXMF", "orderItems": [{"id": "cmmqug0ee02p81rruacwbgydq", "price": 97, "product": {"id": "cmgacfywz02l0jiq7w4etqdvi", "name": "Mentoria Junção Milionária", "externalId": null}}], "trackProps": {"ip": "200.150.246.6", "fbp": "fb.2.1773523979697.706789089758667911", "isUpsell": false, "user_agent": "Mozilla/5.0 (Linux; Android 14; moto g14 Build/UTLBS34.102-91-3) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/145.0.7632.159 Mobile Safari/537.36", "affiliate_code": "h7xrif5"}, "transaction": {"id": "cmmqug0fw02pf1rrumchk0t8c", "amount": 97, "status": "PENDING", "payedAt": null, "acquirer": "Pagar.me", "currency": "BRL", "producer": {"id": "cmga5fa0l00e445zpzpyyk4l8", "name": "Arthur Fernandes Santos", "email": "alexsandrosf3@gmail.com", "phone": "(31) 99946-1179"}, "createdAt": "2026-03-14T21:34:37.602Z", "identifier": "app.applyfy.com.br-ORDER-cmmqug0e702p71rruxgt7fcb1", "chargeAmount": 97, "exchangeRate": 1, "installments": 1, "paymentMethod": "PIX", "originalAmount": 97, "pixInformation": {"id": "cmmqug1ye02pk1rru35h7ix85", "image": "https://api.pagar.me/core/v5/transactions/tran_a3XLZojT1sakrdbn/qrcode?payment_method=pix", "qrCode": "00020101021226820014br.gov.bcb.pix2560pix.stone.com.br/pix/v2/be5ec637-5f9b-46c8-a476-b436246728f2520400005303986540597.005802BR5925Pagar Me Instituicao De P6014RIO DE JANEIRO6229052546f27d3c1b377ce08a42eba1a63048A24", "createdAt": "2026-03-14T21:34:39.578Z", "expiresAt": null, "updatedAt": "2026-03-14T21:34:39.578Z", "endToEndId": null, "description": null, "transactionId": "cmmqug0fw02pf1rrumchk0t8c"}, "originalCurrency": "BRL", "boletoInformation": null}, "subscription": null}	2026-03-14 21:34:40.916602+00
132	cmmqug0fw02pf1rrumchk0t8c	TRANSACTION_PAID	2HKSXMF	\N	{"event": "TRANSACTION_PAID", "split": {"commissions": [{"type": "product-owner", "amount": 17.67, "producerId": "cmga5fa0l00e445zpzpyyk4l8", "splitAccount": {"id": "cmgacacwd02jgnxf02f7sad9w", "status": "APPROVED", "acquirer": "pagar_me", "currency": "BRL", "createdAt": "2025-10-03T04:23:47.917Z", "updatedAt": "2025-10-03T04:23:52.352Z", "customData": {}, "externalId": "re_cmgacacq05lwu0l9t7nn0a3s6", "producerId": "cmga5fa0l00e445zpzpyyk4l8", "transfered": 0, "errorMessage": null, "waitingFunds": 0, "availableBalance": 0}}, {"type": "affiliate", "amount": 72, "producerId": "cmjd76jqv01gwjt1ke6ksmrtm", "splitAccount": {"id": "cmkpk62dx00x31rn0apzklww0", "status": "APPROVED", "acquirer": "pagar_me", "currency": "BRL", "createdAt": "2026-01-22T14:39:46.581Z", "updatedAt": "2026-01-22T14:40:02.296Z", "customData": {}, "externalId": "re_cmkpk62vqb7x40l9tmq8y3k59", "producerId": "cmjd76jqv01gwjt1ke6ksmrtm", "transfered": 0, "errorMessage": null, "waitingFunds": 0, "availableBalance": 0}}], "totalOwnerFee": 7.33}, "token": "nnsgh0ys", "client": {"id": "cmmqucoib02oe1yruo7w2dgbd", "cpf": "215.686.077-76", "cnpj": null, "name": "Wellington Leandro de castro blois", "email": "wellingtonleandro755@gmail.com", "phone": "+5521966967919", "address": null}, "offerCode": "2HKSXMF", "orderItems": [{"id": "cmmqug0ee02p81rruacwbgydq", "price": 97, "product": {"id": "cmgacfywz02l0jiq7w4etqdvi", "name": "Mentoria Junção Milionária", "externalId": null}}], "trackProps": {"ip": "200.150.246.6", "fbp": "fb.2.1773523979697.706789089758667911", "isUpsell": false, "user_agent": "Mozilla/5.0 (Linux; Android 14; moto g14 Build/UTLBS34.102-91-3) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/145.0.7632.159 Mobile Safari/537.36", "affiliate_code": "h7xrif5"}, "transaction": {"id": "cmmqug0fw02pf1rrumchk0t8c", "amount": 97, "status": "COMPLETED", "payedAt": "2026-03-14T21:35:18.957Z", "acquirer": "Pagar.me", "currency": "BRL", "producer": {"id": "cmga5fa0l00e445zpzpyyk4l8", "name": "Arthur Fernandes Santos", "email": "alexsandrosf3@gmail.com", "phone": "(31) 99946-1179"}, "createdAt": "2026-03-14T21:34:37.602Z", "identifier": "app.applyfy.com.br-ORDER-cmmqug0e702p71rruxgt7fcb1", "chargeAmount": 97, "exchangeRate": 1, "installments": 1, "paymentMethod": "PIX", "originalAmount": 97, "pixInformation": {"id": "cmmqug1ye02pk1rru35h7ix85", "image": "https://api.pagar.me/core/v5/transactions/tran_a3XLZojT1sakrdbn/qrcode?payment_method=pix", "qrCode": "00020101021226820014br.gov.bcb.pix2560pix.stone.com.br/pix/v2/be5ec637-5f9b-46c8-a476-b436246728f2520400005303986540597.005802BR5925Pagar Me Instituicao De P6014RIO DE JANEIRO6229052546f27d3c1b377ce08a42eba1a63048A24", "createdAt": "2026-03-14T21:34:39.578Z", "expiresAt": null, "updatedAt": "2026-03-14T21:34:39.578Z", "endToEndId": null, "description": null, "transactionId": "cmmqug0fw02pf1rrumchk0t8c"}, "originalCurrency": "BRL", "boletoInformation": null}, "subscription": null}	2026-03-14 21:35:20.354079+00
\.


--
-- Data for Name: export_runs; Type: TABLE DATA; Schema: public; Owner: applyfy
--

COPY public.export_runs (id, run_at, rows_count, ok_count, timeout_count, erro_count, data) FROM stdin;
1	2026-03-14 17:42:07.658643+00	0	0	0	0	{"log_rows": [], "resultados": []}
2	2026-03-14 17:48:10.613143+00	0	0	0	0	{"log_rows": [], "resultados": []}
\.


--
-- Data for Name: financeiro_categorias; Type: TABLE DATA; Schema: public; Owner: applyfy
--

COPY public.financeiro_categorias (id, nome, tipo, ativa, created_at) FROM stdin;
1	Vendas	receita	t	2026-03-14 19:55:15.739984+00
2	Serviços	receita	t	2026-03-14 19:55:15.739984+00
3	Salários	despesa	t	2026-03-14 19:55:15.739984+00
4	Luz	despesa	t	2026-03-14 19:55:15.739984+00
5	Água	despesa	t	2026-03-14 19:55:15.739984+00
6	Aluguel	despesa	t	2026-03-14 19:55:15.739984+00
7	Outros	despesa	t	2026-03-14 19:55:15.739984+00
\.


--
-- Data for Name: financeiro_lancamentos; Type: TABLE DATA; Schema: public; Owner: applyfy
--

COPY public.financeiro_lancamentos (id, data, valor, tipo, categoria_id, descricao, natureza_dfc, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: saldos_historico; Type: TABLE DATA; Schema: public; Owner: applyfy
--

COPY public.saldos_historico (run_at, email, nome, saldo_pendente, saldo_retido, saldo_disponivel, total_sacado, vendas_liquidas, indicacao, outros) FROM stdin;
2026-03-14 18:25:55.818609+00	cantorleley@gmail.com	Wanderley Gomes dos Santos	0.00	0.00	0.00	0.00	0.00	0.00	0.00
2026-03-14 18:25:58.853329+00	cantorleley@gmail.com	Wanderley Gomes dos Santos	0.00	0.00	0.00	0.00	0.00	0.00	0.00
2026-03-14 18:26:27.585068+00	cantorleley@gmail.com	Wanderley Gomes dos Santos	0.00	0.00	0.00	0.00	0.00	0.00	0.00
2026-03-14 18:25:55.818609+00	nathasrrodrigues@gmail.com	Nathã Rodrigues	0.00	3.11	285.24	0.00	288.36	0.00	0.00
2026-03-14 18:26:27.585068+00	nathasrrodrigues@gmail.com	Nathã Rodrigues	0.00	3.11	285.24	0.00	288.36	0.00	0.00
2026-03-14 18:25:58.853329+00	nathasrrodrigues@gmail.com	Nathã Rodrigues	0.00	3.11	285.24	0.00	288.36	0.00	0.00
2026-03-14 18:25:58.853329+00	enzovicentini03@gmail.com	Enzo Vicentini	0.00	0.00	0.00	0.00	0.00	0.00	0.00
2026-03-14 18:25:55.818609+00	enzovicentini03@gmail.com	Enzo Vicentini	0.00	0.00	0.00	0.00	0.00	0.00	0.00
2026-03-14 18:26:27.585068+00	enzovicentini03@gmail.com	Enzo Vicentini	0.00	0.00	0.00	0.00	0.00	0.00	0.00
2026-03-14 18:25:58.853329+00	williamcdc25@gmail.com	WILLIAM DELMIRO COSTA BARBOSA	0.00	0.00	0.00	0.00	0.00	0.00	0.00
2026-03-14 18:25:55.818609+00	williamcdc25@gmail.com	WILLIAM DELMIRO COSTA BARBOSA	0.00	0.00	0.00	0.00	0.00	0.00	0.00
2026-03-14 18:26:27.585068+00	williamcdc25@gmail.com	WILLIAM DELMIRO COSTA BARBOSA	0.00	0.00	0.00	0.00	0.00	0.00	0.00
2026-03-14 18:25:58.853329+00	vgabrielloli221@gmail.com	Vitor Gabriel Cagliari Loli	0.00	0.00	0.00	0.00	0.00	0.00	0.00
2026-03-14 18:25:55.818609+00	vgabrielloli221@gmail.com	Vitor Gabriel Cagliari Loli	0.00	0.00	0.00	0.00	0.00	0.00	0.00
2026-03-14 18:26:27.585068+00	vgabrielloli221@gmail.com	Vitor Gabriel Cagliari Loli	0.00	0.00	0.00	0.00	0.00	0.00	0.00
2026-03-14 18:25:58.853329+00	iracidasilva080@gmail.com	Iraci da silva	0.00	0.00	0.00	0.00	0.00	0.00	0.00
2026-03-14 18:25:55.818609+00	iracidasilva080@gmail.com	Iraci da silva	0.00	0.00	0.00	0.00	0.00	0.00	0.00
2026-03-14 18:26:27.585068+00	iracidasilva080@gmail.com	Iraci da silva	0.00	0.00	0.00	0.00	0.00	0.00	0.00
2026-03-14 18:25:58.853329+00	mariliapessoa@msn.com	Marilia Auxiliadora Pessoa Thomasky	0.00	0.00	0.00	0.00	0.00	0.00	0.00
2026-03-14 18:25:55.818609+00	mariliapessoa@msn.com	Marilia Auxiliadora Pessoa Thomasky	0.00	0.00	0.00	0.00	0.00	0.00	0.00
2026-03-14 18:26:27.585068+00	mariliapessoa@msn.com	Marilia Auxiliadora Pessoa Thomasky	0.00	0.00	0.00	0.00	0.00	0.00	0.00
2026-03-14 18:25:58.853329+00	fabianamkt.osf@gmail.com	Fabiana da Silva Francisco Fideles	0.00	0.00	0.00	0.00	0.00	0.00	0.00
2026-03-14 18:25:55.818609+00	fabianamkt.osf@gmail.com	Fabiana da Silva Francisco Fideles	0.00	0.00	0.00	0.00	0.00	0.00	0.00
2026-03-14 18:25:58.853329+00	vgads010203@gmail.com	Victor Gabriel da Silva Souza	0.00	0.00	0.00	0.00	0.00	0.00	0.00
2026-03-14 18:26:27.585068+00	fabianamkt.osf@gmail.com	Fabiana da Silva Francisco Fideles	0.00	0.00	0.00	0.00	0.00	0.00	0.00
2026-03-14 18:25:58.853329+00	marquinhobellosouza@gmail.com	marcos	0.00	0.00	0.00	0.00	0.00	0.00	0.00
2026-03-14 18:25:58.853329+00	wellzimedit@gmail.com	Israel Davi	0.00	0.00	0.00	0.00	0.00	0.00	0.00
2026-03-14 18:25:55.818609+00	marquinhobellosouza@gmail.com	marcos	0.00	0.00	0.00	0.00	0.00	0.00	0.00
2026-03-14 18:26:27.585068+00	marquinhobellosouza@gmail.com	marcos	0.00	0.00	0.00	0.00	0.00	0.00	0.00
2026-03-14 18:25:58.853329+00	anfp30@gmail.com	Andreia Regina Vanoni Cardoso	0.00	0.00	0.00	0.00	0.00	0.00	0.00
2026-03-14 18:25:55.818609+00	anfp30@gmail.com	Andreia Regina Vanoni Cardoso	0.00	0.00	0.00	0.00	0.00	0.00	0.00
\.


--
-- Name: applyfy_transactions_id_seq; Type: SEQUENCE SET; Schema: public; Owner: applyfy
--

SELECT pg_catalog.setval('public.applyfy_transactions_id_seq', 133, true);


--
-- Name: export_runs_id_seq; Type: SEQUENCE SET; Schema: public; Owner: applyfy
--

SELECT pg_catalog.setval('public.export_runs_id_seq', 2, true);


--
-- Name: financeiro_categorias_id_seq; Type: SEQUENCE SET; Schema: public; Owner: applyfy
--

SELECT pg_catalog.setval('public.financeiro_categorias_id_seq', 7, true);


--
-- Name: financeiro_lancamentos_id_seq; Type: SEQUENCE SET; Schema: public; Owner: applyfy
--

SELECT pg_catalog.setval('public.financeiro_lancamentos_id_seq', 1, false);


--
-- Name: applyfy_offer_producer applyfy_offer_producer_pkey; Type: CONSTRAINT; Schema: public; Owner: applyfy
--

ALTER TABLE ONLY public.applyfy_offer_producer
    ADD CONSTRAINT applyfy_offer_producer_pkey PRIMARY KEY (offer_code);


--
-- Name: applyfy_producer_taxes applyfy_producer_taxes_pkey; Type: CONSTRAINT; Schema: public; Owner: applyfy
--

ALTER TABLE ONLY public.applyfy_producer_taxes
    ADD CONSTRAINT applyfy_producer_taxes_pkey PRIMARY KEY (producer_id);


--
-- Name: applyfy_transactions applyfy_transactions_pkey; Type: CONSTRAINT; Schema: public; Owner: applyfy
--

ALTER TABLE ONLY public.applyfy_transactions
    ADD CONSTRAINT applyfy_transactions_pkey PRIMARY KEY (id);


--
-- Name: export_runs export_runs_pkey; Type: CONSTRAINT; Schema: public; Owner: applyfy
--

ALTER TABLE ONLY public.export_runs
    ADD CONSTRAINT export_runs_pkey PRIMARY KEY (id);


--
-- Name: financeiro_categorias financeiro_categorias_pkey; Type: CONSTRAINT; Schema: public; Owner: applyfy
--

ALTER TABLE ONLY public.financeiro_categorias
    ADD CONSTRAINT financeiro_categorias_pkey PRIMARY KEY (id);


--
-- Name: financeiro_lancamentos financeiro_lancamentos_pkey; Type: CONSTRAINT; Schema: public; Owner: applyfy
--

ALTER TABLE ONLY public.financeiro_lancamentos
    ADD CONSTRAINT financeiro_lancamentos_pkey PRIMARY KEY (id);


--
-- Name: saldos_historico saldos_historico_pkey; Type: CONSTRAINT; Schema: public; Owner: applyfy
--

ALTER TABLE ONLY public.saldos_historico
    ADD CONSTRAINT saldos_historico_pkey PRIMARY KEY (run_at, email);


--
-- Name: applyfy_transactions uq_applyfy_transaction_event; Type: CONSTRAINT; Schema: public; Owner: applyfy
--

ALTER TABLE ONLY public.applyfy_transactions
    ADD CONSTRAINT uq_applyfy_transaction_event UNIQUE (transaction_id, event);


--
-- Name: idx_applyfy_producer_taxes_email; Type: INDEX; Schema: public; Owner: applyfy
--

CREATE INDEX idx_applyfy_producer_taxes_email ON public.applyfy_producer_taxes USING btree (email);


--
-- Name: idx_applyfy_transactions_event; Type: INDEX; Schema: public; Owner: applyfy
--

CREATE INDEX idx_applyfy_transactions_event ON public.applyfy_transactions USING btree (event);


--
-- Name: idx_applyfy_transactions_offer_code; Type: INDEX; Schema: public; Owner: applyfy
--

CREATE INDEX idx_applyfy_transactions_offer_code ON public.applyfy_transactions USING btree (offer_code);


--
-- Name: idx_applyfy_transactions_received_at; Type: INDEX; Schema: public; Owner: applyfy
--

CREATE INDEX idx_applyfy_transactions_received_at ON public.applyfy_transactions USING btree (received_at);


--
-- Name: idx_financeiro_categorias_tipo; Type: INDEX; Schema: public; Owner: applyfy
--

CREATE INDEX idx_financeiro_categorias_tipo ON public.financeiro_categorias USING btree (tipo);


--
-- Name: idx_financeiro_lancamentos_categoria; Type: INDEX; Schema: public; Owner: applyfy
--

CREATE INDEX idx_financeiro_lancamentos_categoria ON public.financeiro_lancamentos USING btree (categoria_id);


--
-- Name: idx_financeiro_lancamentos_data; Type: INDEX; Schema: public; Owner: applyfy
--

CREATE INDEX idx_financeiro_lancamentos_data ON public.financeiro_lancamentos USING btree (data);


--
-- Name: idx_financeiro_lancamentos_tipo; Type: INDEX; Schema: public; Owner: applyfy
--

CREATE INDEX idx_financeiro_lancamentos_tipo ON public.financeiro_lancamentos USING btree (tipo);


--
-- Name: idx_saldos_historico_email; Type: INDEX; Schema: public; Owner: applyfy
--

CREATE INDEX idx_saldos_historico_email ON public.saldos_historico USING btree (email);


--
-- Name: idx_saldos_historico_run_at; Type: INDEX; Schema: public; Owner: applyfy
--

CREATE INDEX idx_saldos_historico_run_at ON public.saldos_historico USING btree (run_at);


--
-- Name: financeiro_lancamentos financeiro_lancamentos_categoria_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: applyfy
--

ALTER TABLE ONLY public.financeiro_lancamentos
    ADD CONSTRAINT financeiro_lancamentos_categoria_id_fkey FOREIGN KEY (categoria_id) REFERENCES public.financeiro_categorias(id) ON DELETE SET NULL;


--
-- PostgreSQL database dump complete
--

\unrestrict OSDGyxRpP3tPFc0TfLkVHwll3XqwlSrKIkcrW8U805nBj7FtFqIXfa70g99fUPT

