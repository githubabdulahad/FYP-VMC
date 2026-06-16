from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('coding', '0001_initial'),
        ('ingestion', '0003_create_uploadrecord_table'),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
                CREATE TABLE IF NOT EXISTS coding_codingresult (
                    id bigserial PRIMARY KEY,
                    upload_record_id bigint NOT NULL UNIQUE REFERENCES ingestion_uploadrecord(id) DEFERRABLE INITIALLY DEFERRED,
                    user_id bigint NOT NULL REFERENCES accounts_user(id) DEFERRABLE INITIALLY DEFERRED,
                    soap_note jsonb NOT NULL DEFAULT '{}'::jsonb,
                    icd_codes jsonb NOT NULL DEFAULT '[]'::jsonb,
                    cpt_codes jsonb NOT NULL DEFAULT '[]'::jsonb,
                    snomed_codes jsonb NOT NULL DEFAULT '[]'::jsonb,
                    summary text NOT NULL DEFAULT '',
                    confidence double precision NULL,
                    raw_llm_output text NOT NULL DEFAULT '',
                    review_status varchar(20) NOT NULL DEFAULT 'pending',
                    created_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP
                );

                CREATE INDEX IF NOT EXISTS coding_codingresult_user_id_8e4b6f2d_idx
                    ON coding_codingresult (user_id);

                CREATE INDEX IF NOT EXISTS coding_codingresult_created_at_7f8c2d3a_idx
                    ON coding_codingresult (created_at DESC);
            """,
            reverse_sql="""
                DROP TABLE IF EXISTS coding_codingresult CASCADE;
            """,
        ),
    ]