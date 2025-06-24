from google.cloud.sql.connector import Connector, IPTypes
import pg8000
from sqlalchemy import text, create_engine

ICN = "jukebox-446711:southamerica-east1:jukebox" 

def get_super_conn() -> pg8000.dbapi.Connection:
    """Initializes a connection to the Cloud SQL PostgreSQL instance."""
    connector = Connector()
    conn = connector.connect(
        ICN,
        "pg8000",
        user="postgres",
        password="k]a-hXIRZ0taLT}K",
        db="postgres",
        ip_type=IPTypes.PUBLIC  # or IPTypes.PRIVATE if applicable
    )
    return conn

def set_new_user_access(DB_USER):
    # Garantir acesso a novo usuário
    print("my log - 006 - garantindo acessos ao usuário:", DB_USER)
    query = f"""
GRANT USAGE ON SCHEMA public TO {DB_USER};
GRANT CONNECT ON DATABASE postgres TO {DB_USER};
GRANT SELECT, INSERT ON artistas TO {DB_USER};
GRANT USAGE ON SEQUENCE public.artistas_id_seq TO {DB_USER};
GRANT SELECT ON SEQUENCE public.artistas_id_seq TO {DB_USER};
GRANT SELECT, INSERT, UPDATE ON configurations TO {DB_USER};
GRANT USAGE ON SEQUENCE public.configurations_id_seq TO {DB_USER};
GRANT SELECT ON SEQUENCE public.configurations_id_seq TO {DB_USER};
GRANT SELECT, INSERT ON generos TO {DB_USER};
GRANT USAGE ON SEQUENCE public.generos_id_seq TO {DB_USER};
GRANT SELECT ON SEQUENCE public.generos_id_seq TO {DB_USER};
GRANT SELECT, INSERT ON likes TO {DB_USER};
GRANT USAGE ON SEQUENCE public.likes_id_seq TO {DB_USER};
GRANT SELECT ON SEQUENCE public.likes_id_seq TO {DB_USER};
GRANT SELECT, INSERT ON pedidos TO {DB_USER};
GRANT USAGE ON SEQUENCE public.pedidos_id_seq TO {DB_USER};
GRANT SELECT ON SEQUENCE public.pedidos_id_seq TO {DB_USER};
GRANT SELECT, INSERT ON tracks TO {DB_USER};
GRANT SELECT, INSERT ON users TO {DB_USER};
GRANT USAGE ON SEQUENCE public.users_id_seq TO {DB_USER};
GRANT SELECT ON SEQUENCE public.users_id_seq TO {DB_USER};
GRANT SELECT, INSERT, UPDATE ON sessions TO {DB_USER};
GRANT USAGE ON SEQUENCE public.sessions_id_seq TO {DB_USER};
GRANT SELECT ON SEQUENCE public.sessions_id_seq TO {DB_USER};
GRANT SELECT, INSERT, UPDATE ON instances TO {DB_USER};
GRANT SELECT, INSERT, UPDATE ON genre_lists TO {DB_USER};
GRANT USAGE ON SEQUENCE public.genre_lists_id_seq TO {DB_USER};
GRANT SELECT ON SEQUENCE public.genre_lists_id_seq TO {DB_USER};
GRANT SELECT, INSERT, UPDATE, DELETE ON promos TO {DB_USER};
GRANT USAGE ON SEQUENCE public.promos_id_seq TO {DB_USER};
GRANT SELECT ON SEQUENCE public.promos_id_seq TO {DB_USER};
"""
    try:
        print("my log - 007 - Logando com superuser")
        pool = create_engine("postgresql+pg8000://", creator=get_super_conn)
        with pool.connect() as conn:
            conn.execute(text(query))
            conn.commit()
        return True
    except Exception as e:
        print("my log - 007 - Erro ao conectar superuser ao banco de dados:", e)
        return False    

def create_intance(instance,cliente, cloud_url ):
    query = f"""
INSERT INTO instances (instance, cliente, cloud_url)
VALUES ('{instance}', '{cliente}', '{cloud_url}');
    """
    try:
        print("criando instance")
        pool = create_engine("postgresql+pg8000://", creator=get_super_conn)
        with pool.connect() as conn:
            conn.execute(text(query))
            conn.commit()
        return True
    except Exception as e:
        print("my log - 007 - Erro ao criar instance:", e)
        return False  