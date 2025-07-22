import os
from dotenv import load_dotenv
import boto3
import time
from datetime import datetime, timedelta
from typing import Dict, Any

load_dotenv()

R2_ENDPOINT = os.getenv("R2_ENDPOINT")
R2_ACCESS_KEY = os.getenv("R2_ACCESS_KEY")
R2_SECRET_KEY = os.getenv("R2_SECRET_KEY")
R2_BUCKET_NAME = os.getenv("R2_BUCKET_NAME")

def get_r2_client():
    return boto3.client(
        's3',
        endpoint_url = R2_ENDPOINT,
        aws_access_key=R2_ACCESS_KEY,
        aws_secret_access_key=R2_SECRET_KEY,
        region_name='auto'
    )

def upload_pdf_to_r2(pdf_path: str, order_id: str) -> str:
    try:
        s3_client = get_r2_client()

        date_prefix = datetime.now().strftime("%Y/%m")
        object_key = f"{date_prefix}/order_{order_id}.pdf"

        expiration_date = datetime.now() + timedelta(days=365)

        with open(pdf_path, 'rb') as pdf_file:
            s3_client.upload_fileobj(
                pdf_file,
                R2_BUCKET_NAME,
                object_key,
                ExtraArgs = {
                    'Metadata': {
                        'order-id': str(order_id),
                        'created-at': datetime.now().isoformat(),
                        'expires-at': expiration_date.isoformat()
                    },
                    'ContentType': 'application/pdf'
                }
            )

        print(f"PDF uploaded to R2: {object_key}")
        return object_key
    except Exception as e:
        print(f"Failed to upload PDF to R2: {e}")
        raise

def get_pdf_download_url(r2_object_key: str, expires_in: int = 3600) -> str:
    try:
        s3_client = get_r2_client()
        url = s3_client.generate_presigned_url(
            'get-object',
            Params = {'Bucket': R2_BUCKET_NAME, 'Key': r2_object_key},
            ExpiresIn = expires_in
        )
        return url
    except Exception as e:
        print(f"Failed to generate download URL: {e}")
        raise

def setup_r2_lifecycle_policy():
    s3_client = get_r2_client()

    lifecycle_config = {
        'Rules': [
            {
                'ID': 'DeleteAfterOneYear',
                'Status': 'Enabled',
                'Filter': {'Prefix': ''},
                'Expiration': {'Days': 365}
            }
        ]
    }

    try:
        s3_client.put_bucket_lifecycle_configuration(
            Bucket=R2_BUCKET_NAME,
            LifecycleConfiguration=lifecycle_config
        )
        print(f"Lifecycle policy set up successfully!")
    except Exception as e:
        print(f"Failed to set up lifecycle policy: {e}")
        raise