# NEXT STEPS: qué está hecho y qué falta (nube AWS)

> **Resumen en una línea:** todo el código está terminado y probado en local. Toda la infraestructura AWS está escrita en Terraform, pero **todavía no se ha creado nada en AWS**. Falta ejecutar el despliegue, meter la API key en Secrets Manager y probar en la nube siguiendo este documento.

---

## 1. Estado actual

### ✅ Hecho y probado (sin AWS)

| Qué | Cómo se ha probado |
|---|---|
| Backend: 12 agentes, LangGraph, SSE, follow-ups, briefings, email, audio TTS e infografía | 122 tests `pytest` + 7 tests *live* contra OpenRouter, Yahoo, SEC y GDELT reales con nuestra clave |
| **Vídeo** (Video Agent: voz + diapositivas en una sola llamada a Gemini 3.8 Flash) | Tests con fakes + test *live* con `demo_data/northwind_webinar.mp4` (≈ 0,03 $, 4 diapositivas con cifras exactas) |
| **Búsqueda semántica multimodal** (`/app/search`, búsqueda por imagen, recuperación en follow-ups; Gemini Embedding 2) | Tests de API/índice + test *live*: "what did the CFO say about gross margin" devuelve el fragmento exacto del vídeo (00:56) |
| Acceso solo por invitación (lista de emails) y límites diarios | Tests (`backend/tests/test_access_control.py`), incluido el Lambda de Cognito |
| Adaptadores AWS (DynamoDB, S3 prefirmado, SQS ack/reintento/DLQ, Secrets Manager, SES) | Tests con **moto** (AWS simulado en memoria) |
| Camino AWS completo (API + worker en otro contenedor + SQS + DynamoDB + S3 + Secrets Manager + scheduler idempotente) | `docker compose --profile aws-local up` sobre **LocalStack** (AWS simulado en Docker, en local) |
| Frontend (todas las páginas, móvil, modo demo) | 27 tests Vitest + E2E con Playwright en la app real; **verifica automáticamente que ningún enlace da 404** |
| Imágenes Docker backend y frontend | `docker compose build` OK |
| Terraform | `terraform fmt -check` y `terraform validate` OK |

### ❌ No hecho (hay que hacerlo vosotros)

| Qué | Dónde |
|---|---|
| `terraform apply`: crear la infraestructura en la cuenta AWS | Paso 4 |
| Construir y subir la imagen a ECR, y publicar el frontend en S3 + CloudFront | Paso 4 (`scripts/deploy.sh`) |
| **Guardar la API key de OpenRouter en Secrets Manager** | Paso 5 |
| Verificar los emails de SES (hacer clic en los correos de AWS) | Paso 6 |
| Todas las pruebas en la nube | Paso 7 |
| Grabar la demo y añadir la URL desplegada al README | Paso 9 |

---

## 2. ¿Dominio? → No hace falta, usamos CloudFront

Terraform crea una distribución **CloudFront** y su URL `https://dxxxxxxxx.cloudfront.net` es "nuestro dominio":
- HTTPS gratis.
- Una sola URL para la web y la API: `/api/*` va al backend, así que no hay problemas de CORS.
- Cognito funciona sin dominio.
- SES funciona verificando un email.

La URL sale al final del despliegue (`terraform output app_url`).

## 3. Qué crea Terraform (todo, nada a mano)

`terraform/environments/dev` crea:

- **Red**: VPC, 2 subnets públicas, internet gateway y security groups. Sin NAT, para ahorrar.
- **CloudFront**: la URL pública, con su función de la SPA y la contraseña opcional.
- **Web y API**: S3 privado para el frontend; ALB, que solo acepta tráfico de CloudFront.
- **Cómputo**: ECR, cluster ECS Fargate (servicio API + servicio worker en Spot) y una tarea *scheduler* con su CloudWatch Logs.
- **Datos y colas**: 8 tablas DynamoDB, bucket S3 privado de uploads (CORS, cifrado, expiración a 90 días), 2 colas SQS con sus DLQ.
- **Programación**: EventBridge Scheduler cada 15 minutos.
- **Usuarios y acceso**: Cognito (user pool + cliente SPA) y el **Lambda de lista de invitados**.
- **Secretos y permisos**: Secrets Manager (solo el "contenedor" del secreto) e IAM con mínimo privilegio.
- **Email**: identidades de SES.

**Lo único que NO puede hacer Terraform (por diseño):**
1. Meter el **valor** de la API key en Secrets Manager. Si lo hiciera quedaría guardado en el `tfstate`; lo hace `set_secrets.sh` (paso 5).
2. Hacer clic en los emails de verificación de SES (paso 6).
3. Poner un límite de gasto a la clave en OpenRouter. Es fuera de AWS; recomendado en el paso 8.

## 4. Despliegue (en este orden)

**Requisitos en el PC:**
- AWS CLI v2 con las credenciales de la cuenta de créditos. Comprobar con `aws sts get-caller-identity`.
- Terraform ≥ 1.6.
- Docker Desktop **arrancado**.
- Node 20+ y Python 3.11+.
- El `.env` con la API key (`OPEN_ROUTER_API_KEY=...`). **Nunca se sube a git.**

```bash
# 4.1 Configuración (fichero NO versionado)
cp terraform/environments/dev/terraform.tfvars.example terraform/environments/dev/terraform.tfvars
#     Editarlo:
#       allowed_emails = ["vuestro1@gmail.com", "vuestro2@gmail.com", "email-del-profe@..."]   ← quién puede usar la app
#       site_password  = "una-contraseña"     ← opcional: contraseña para ver la web
#       ses_from_email = "..."                ← opcional: remitente de los emails

# 4.2 Despliegue completo (Windows: ./scripts/deploy.ps1)
./scripts/deploy.sh
```

`deploy.sh` hace lo siguiente, en este orden:

1. Crea el ECR.
2. Construye la imagen `linux/amd64` y la sube.
3. Ejecuta `terraform apply` de todo.
4. Compila el frontend con los ids de Cognito y lo sube a S3.
5. Invalida CloudFront.
6. Reinicia ECS.

**Tiempo estimado:** 15–25 minutos; CloudFront es lo más lento. Al terminar imprime la URL.

## 5. API keys en Secrets Manager (obligatorio)

Terraform crea un secreto vacío llamado `signalroom/dev/app`. Hay que rellenarlo:

```bash
./scripts/set_secrets.sh            # Windows: ./scripts/set_secrets.ps1
./scripts/deploy.sh --restart-only  # las tareas leen el secreto al arrancar
```

- El script lee `.env` y sube un JSON con estas claves:
  - `OPENROUTER_API_KEY` (también acepta `OPEN_ROUTER_API_KEY` en el `.env`);
  - `ALPHAVANTAGE_API_KEY` y `FRED_API_KEY`, opcionales y vacías si no las tenéis;
  - `SEC_USER_AGENT` y `SES_FROM_EMAIL`.
- No imprime valores y borra el fichero temporal.
- **Comprobar**: `curl https://<app_url>/api/v1/health` debe mostrar `"providers": {"openrouter": true, ...}`. Si sale `false`, el secreto está vacío o las tareas no se han reiniciado.
- **Para ver qué claves tiene** (sin ver los valores): `aws secretsmanager get-secret-value --secret-id signalroom/dev/app --query SecretString --output text | python -c "import sys,json;print(list(json.load(sys.stdin)))"`
- **Para cambiar o rotar la clave**: editar `.env`, volver a lanzar `set_secrets.sh` y luego `--restart-only`.
- La clave **no** está en Terraform, ni en las imágenes, ni en GitHub, ni llega al navegador.

## 6. Protección anti-gasto (que no lo use cualquiera)

Ya está implementado. Solo hay que rellenar `terraform.tfvars`:

| Capa | Variable | Qué hace |
|---|---|---|
| Lista de invitados en el alta | `allowed_emails` | Un Lambda de Cognito rechaza el registro de cualquier email que no esté en la lista. Admite emails exactos y dominios con `@dominio.com`. |
| Lista de invitados en la API | la misma | Cada petición a la API comprueba el email del usuario. Si quitáis a alguien de la lista y hacéis `terraform apply`, pierde el acceso al momento. |
| Contraseña de la web | `site_password` | CloudFront pide usuario (`site_username`, por defecto `signalroom`) y contraseña antes de mostrar nada. Útil para pasársela solo al profe. |
| Límites diarios | `max_investigations_per_day` (20), `max_briefings_per_day` (5) | Por usuario. Al superarlos sale un mensaje amable. |
| Rate limit | — | Límite de peticiones por minuto en la API. |

Para cambiar la lista: editar `terraform.tfvars` y ejecutar `terraform -chdir=terraform/environments/dev apply`. El Lambda y la API se actualizan.

**SES (emails):**
- Tras el `apply`, AWS envía un email de verificación al remitente y a cada destinatario de `ses_sandbox_recipients`. Hay que hacer clic en todos.
- En el sandbox de SES solo se puede enviar a emails verificados.
- Detalles en `docs/email_setup.md`.

## 7. Checklist de pruebas en la nube (pendiente)

- [ ] `GET <app_url>/api/v1/health` → `backend: aws`, `auth: cognito`, `checks.database/storage: ok`, `providers.openrouter: true`.
- [ ] Si hay `site_password`, el navegador pide la contraseña. Sin ella no se ve nada; con ella carga la landing.
- [ ] Los enlaces del footer funcionan: About, Privacy, Terms, Methodology, Pricing y Daily briefing. Recargar `/app/dashboard` no debe dar error, porque la función de CloudFront reescribe la ruta.
- [ ] **Alta con un email NO invitado** → mensaje "This SignalRoom demo is invite-only…" y la cuenta no se crea.
- [ ] **Alta con un email invitado**: llega el código, se verifica y se puede entrar. Probar también "Forgot password" y "Sign out".
- [ ] El dashboard muestra cotizaciones (las tareas salen a internet por IP pública).
- [ ] **Why? sobre NVDA**: el progreso se ve en vivo y la investigación termina en 1–2 minutos.
  - Si el progreso no se mueve en vivo pero al final aparece, el SSE está cayendo a *polling*. Funciona igual, pero conviene revisarlo.
- [ ] **Research con PDF + audio** (`demo_data/northwind_q3_fy2026_results.pdf`, `demo_data/earnings_call.wav`): las subidas van directas a S3.
  - Si dan error de CORS, revisar que `allowed_origins` del bucket de uploads sea exactamente `app_url`.
- [ ] Pestaña "Documents & media": transcripción con hablantes y datos del PDF.
- [ ] **Research con vídeo** (`demo_data/northwind_webinar.mp4`, 1,2 MB): la subida va a S3 y la tarjeta de vídeo muestra diapositivas con timestamp y cifras. Máximo 40 MB por vídeo (subida directa a S3, no pasa por el ALB).
  - El worker descarga el vídeo de S3 y lo manda en base64 a OpenRouter: si falla por timeout con vídeos grandes, subir `AI_TIMEOUT_SECONDS` (variable de entorno del worker).
- [ ] **Search** (menú lateral): buscar "gross margin" → aparecen fragmentos con su timestamp/página y enlazan a la investigación. "Search by image" con `demo_data/nvda_chart.png` (va por el ALB, máx. 5 MB).
  - Si las investigaciones antiguas no salen (se crearon antes de desplegar esto): `python scripts/reindex.py <email o user id>` con la configuración AWS.
  - El modo indicado debe ser "Semantic match · Gemini Embedding 2". Si pone "Keyword match", el modelo de embeddings no responde (revisar el secreto de OpenRouter).
- [ ] Botones **Listen** (audio) y **Create visual brief** (imagen).
- [ ] Follow-up "Does this change the thesis?".
- [ ] **Briefing diario automático**:
  - [ ] En Settings, activarlo con la hora 10–15 minutos en el futuro.
  - [ ] Esperar a la tarea `scheduler` (logs en `/ecs/signalroom-dev/scheduler`).
  - [ ] Comprobar que aparece **un solo** briefing.
- [ ] **Email**: con "Email me the briefing" activado llega el correo (revisar spam) y sus enlaces abren la app.
- [ ] **Límites**: con `max_investigations_per_day = 2`, la tercera investigación da el mensaje de límite (luego volver a 20).
- [ ] **DLQ**: si un trabajo falla 3 veces, el mensaje acaba en `signalroom-dev-investigation-dlq`.
- [ ] **Logs sin secretos**: en CloudWatch Logs Insights, buscar `sk-or` → 0 resultados.
- [ ] Settings → "Delete my investigations…" borra los datos y los ficheros de S3.

## 8. Problemas probables

| Síntoma | Causa | Solución |
|---|---|---|
| Servicio ECS sin tareas sanas | La imagen no existía o el secreto estaba vacío | `deploy.sh` completo y después `set_secrets.sh` + `--restart-only` |
| `providers.openrouter: false` | Secreto vacío o tareas sin reiniciar | Paso 5 |
| 403 "Forbidden" del ALB | Se está entrando por la URL del ALB | Usar siempre la URL de CloudFront |
| "invite-only" con un email que debería entrar | No está en `allowed_emails` o falta el `apply` | Añadirlo y ejecutar `terraform apply` |
| Pantalla en blanco tras desplegar | Caché de CloudFront | `./scripts/deploy.sh --frontend-only` |
| GDELT siempre falla | Límite de peticiones de GDELT | Es esperado: hay *circuit breaker* y las noticias salen de Yahoo |
| No llegan emails | SES en sandbox | Verificar los destinatarios y revisar spam |

**Muy recomendable:** poner un **límite de crédito a la API key en OpenRouter** (https://openrouter.ai/settings/keys). Es la última barrera si algo falla. Coste medido: ≈ 0,003 $ por investigación de texto, ≈ 0,02 $ por una multimodal, ≈ 0,03 $ por un vídeo de 2 min, ≈ 0,0004 $ por indexar una investigación y ≈ 0,07 $ por cada infografía.

## 9. Coste, apagado y entrega

- **Pausar sin borrar**: poner `api_desired_count = 0` y `worker_desired_count = 0` en `terraform.tfvars` y ejecutar `terraform apply`.
- **Borrarlo todo** al acabar: `terraform -chdir=terraform/environments/dev destroy`.
- **Antes de entregar**:
  - [ ] `git status`: **no** aparecen `.env` ni `terraform.tfvars`.
  - [ ] `./scripts/test.sh` en verde.
  - [ ] README actualizado con la URL de CloudFront y el vídeo de la demo (guion en `docs/demo.md`).
- **Opcional**:
  - Estado de Terraform compartido en S3 (`backend.tf.example`).
  - Workflow `Deploy (manual)` con GitHub OIDC: necesita estado remoto y el rol `AWS_DEPLOY_ROLE_ARN`. No guardar claves de AWS en GitHub.
