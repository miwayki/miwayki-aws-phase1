# Runbook AWS — Trial técnico de la Fase Básica validada localmente

## Estado
Aprobado para ejecución inmediata.

## Objetivo
Levantar en AWS la **fase básica ya validada localmente** para una prueba controlada de bring-up + validación E2E técnica, sin pasar todavía a producción, sin Terraform, sin Mautic y sin mover aún el proveedor de modelo a Bedrock.

Este despliegue existe para comprobar que el stack validado localmente puede reproducirse en una EC2 real y quedar listo para pruebas. Al final de la jornada, la instancia podrá apagarse.

## Alcance
Se desplegará únicamente lo ya validado funcionalmente:
- PostgreSQL
- Redis
- Chatwoot
- FastAPI Bridge
- Dify como stack separado
- Nginx solo si el árbol del proyecto ya lo requiere para exponer servicios
- validaciones E2E equivalentes a las cerradas en local

## Fuera de alcance
- Producción definitiva
- Mautic
- Bedrock
- Terraform
- Route 53 / dominio final
- TLS definitivo
- observabilidad completa
- escalado / HA / balanceadores
- Fase 2 funcional

---

# 1. Decisiones congeladas para este trial

Estas decisiones quedan cerradas y no se reabren durante la ejecución:

- **Región AWS:** `us-east-1`
- **Perfil AWS CLI:** perfil administrativo dedicado al proyecto (recomendado: `miwayki-admin`)
- **Sistema operativo:** Ubuntu
- **Arquitectura:** ARM64
- **Instancia objetivo:** `m7g.xlarge`
- **Disco raíz:** `150 GB gp3`
- **IP pública:** Elastic IP
- **Método de despliegue:** AWS CLI + SSH + Git
- **Modo de acceso público inicial:** HTTP temporal controlado
- **Proveedor IA en esta subida:** el mismo ya usado localmente en Dify
- **Dify:** stack separado del core
- **Meta del día:** bring-up + E2E técnico + apagado opcional de la instancia al final

---

# 2. Arquitectura objetivo de esta prueba

La topología a reproducir en AWS es:

`Usuario -> Chatwoot -> Bridge -> Dify -> Bridge -> Chatwoot`

Con estas reglas:
- Chatwoot es el front/inbox humano.
- El Bridge es la capa estratégica y la única dueña de la lógica operativa ya validada.
- Dify permanece separado del core.
- El Bridge consume Dify por hostname interno, no por `127.0.0.1`.
- PostgreSQL y Redis no se exponen públicamente.

---

# 3. Variables de sesión (a exportar en local)

Antes de empezar, en tu Mac exportaremos estas variables:

```bash
export AWS_PROFILE=miwayki-admin
export AWS_REGION=us-east-1
export PROJECT_NAME=miwayki
export INSTANCE_NAME=miwayki-phase1-trial
export KEY_NAME=miwayki-phase1-trial-key
export SG_NAME=miwayki-phase1-trial-sg
export EIP_TAG_NAME=miwayki-phase1-trial-eip
```

Tu IP pública actual para SSH:

```bash
export MYIP=$(curl -s https://checkip.amazonaws.com | tr -d '\n')
echo "${MYIP}/32"
```

---

# 4. Estrategia de código

## Decisión
Se usará **Git como canal principal**.

## Flujo aprobado
1. Crear rama dedicada de despliegue, por ejemplo:
   - `aws-phase1-trial`
2. Confirmar que el árbol local está limpio o que los cambios necesarios están committeados.
3. Hacer `push` al remoto.
4. Clonar la rama exacta en la EC2.

## Razón
Este flujo:
- deja trazabilidad,
- permite rollback,
- evita drift entre local y servidor,
- y reduce errores humanos frente a `scp` o copias manuales.

## Nota
`scp/rsync` solo se usarán si aparece un archivo local imprescindible que todavía no está en Git y no conviene detener el trial para reordenarlo.

---

# 5. Preparación AWS

## 5.1 Validación inicial de CLI

```bash
aws --version
aws configure list-profiles
aws sts get-caller-identity --profile "$AWS_PROFILE"
```

## 5.2 Descubrir VPC y subred pública

Se revisará primero si la default VPC es usable en `us-east-1`. Si lo es, se usará solo para este trial para acelerar la salida. Si no, se elegirá una VPC existente apta con subred pública.

Comandos base:

```bash
aws ec2 describe-vpcs \
  --profile "$AWS_PROFILE" \
  --region "$AWS_REGION" \
  --query 'Vpcs[].{VpcId:VpcId,IsDefault:IsDefault,Cidr:CidrBlock}' \
  --output table

aws ec2 describe-subnets \
  --profile "$AWS_PROFILE" \
  --region "$AWS_REGION" \
  --query 'Subnets[].{SubnetId:SubnetId,VpcId:VpcId,Az:AvailabilityZone,Cidr:CidrBlock,MapPublicIp:MapPublicIpOnLaunch}' \
  --output table
```

## 5.3 Crear key pair nueva

Se creará una llave nueva dedicada al trial:

```bash
aws ec2 create-key-pair \
  --profile "$AWS_PROFILE" \
  --region "$AWS_REGION" \
  --key-name "$KEY_NAME" \
  --key-type ed25519 \
  --query 'KeyMaterial' \
  --output text > "${KEY_NAME}.pem"

chmod 400 "${KEY_NAME}.pem"
```

## 5.4 Crear Security Group dedicado

Reglas mínimas iniciales:
- `22/tcp` solo desde `${MYIP}/32`
- `80/tcp` desde `0.0.0.0/0`

No se abrirán públicamente:
- `5432`
- `6379`
- puertos internos de Chatwoot, Bridge o Dify

Primero crear el SG en la VPC elegida:

```bash
aws ec2 create-security-group \
  --profile "$AWS_PROFILE" \
  --region "$AWS_REGION" \
  --group-name "$SG_NAME" \
  --description "MiWayki phase1 AWS trial" \
  --vpc-id <VPC_ID>
```

Luego abrir SSH:

```bash
aws ec2 authorize-security-group-ingress \
  --profile "$AWS_PROFILE" \
  --region "$AWS_REGION" \
  --group-id <SG_ID> \
  --ip-permissions "IpProtocol=tcp,FromPort=22,ToPort=22,IpRanges=[{CidrIp=${MYIP}/32,Description='Mac actual'}]"
```

Y abrir HTTP:

```bash
aws ec2 authorize-security-group-ingress \
  --profile "$AWS_PROFILE" \
  --region "$AWS_REGION" \
  --group-id <SG_ID> \
  --ip-permissions 'IpProtocol=tcp,FromPort=80,ToPort=80,IpRanges=[{CidrIp=0.0.0.0/0,Description="HTTP temporal"}]'
```

---

# 6. Lanzamiento de la EC2 Ubuntu ARM

## 6.1 Resolver AMI Ubuntu ARM

Se usará Ubuntu Server ARM64 vía SSM Parameter Store.

```bash
aws ssm get-parameter \
  --profile "$AWS_PROFILE" \
  --region "$AWS_REGION" \
  --name /aws/service/canonical/ubuntu/server/24.04/stable/current/arm64/hvm/ebs-gp3/ami-id \
  --query 'Parameter.Value' \
  --output text
```

Guardar el valor en:

```bash
export UBUNTU_AMI=<AMI_ID>
```

## 6.2 Lanzar instancia

```bash
aws ec2 run-instances \
  --profile "$AWS_PROFILE" \
  --region "$AWS_REGION" \
  --image-id "$UBUNTU_AMI" \
  --instance-type m7g.xlarge \
  --key-name "$KEY_NAME" \
  --security-group-ids <SG_ID> \
  --subnet-id <SUBNET_ID> \
  --block-device-mappings '[{"DeviceName":"/dev/sda1","Ebs":{"VolumeSize":150,"VolumeType":"gp3","DeleteOnTermination":true}}]' \
  --tag-specifications "ResourceType=instance,Tags=[{Key=Name,Value=${INSTANCE_NAME}}]" \
  --metadata-options 'HttpTokens=required,HttpEndpoint=enabled' \
  --query 'Instances[0].InstanceId' \
  --output text
```

Guardar el resultado en:

```bash
export INSTANCE_ID=<INSTANCE_ID>
```

## 6.3 Esperar arranque

```bash
aws ec2 wait instance-running \
  --profile "$AWS_PROFILE" \
  --region "$AWS_REGION" \
  --instance-ids "$INSTANCE_ID"
```

## 6.4 Ver detalles

```bash
aws ec2 describe-instances \
  --profile "$AWS_PROFILE" \
  --region "$AWS_REGION" \
  --instance-ids "$INSTANCE_ID" \
  --query 'Reservations[0].Instances[0].{Id:InstanceId,State:State.Name,AZ:Placement.AvailabilityZone,PublicIp:PublicIpAddress,PublicDns:PublicDnsName,PrivateIp:PrivateIpAddress}' \
  --output table
```

---

# 7. Elastic IP

## 7.1 Asignar Elastic IP

```bash
aws ec2 allocate-address \
  --profile "$AWS_PROFILE" \
  --region "$AWS_REGION" \
  --domain vpc \
  --tag-specifications "ResourceType=elastic-ip,Tags=[{Key=Name,Value=${EIP_TAG_NAME}}]"
```

Guardar:
- `AllocationId`
- `PublicIp`

```bash
export EIP_ALLOC_ID=<ALLOCATION_ID>
export EIP_PUBLIC_IP=<ELASTIC_IP>
```

## 7.2 Asociar Elastic IP

```bash
aws ec2 associate-address \
  --profile "$AWS_PROFILE" \
  --region "$AWS_REGION" \
  --instance-id "$INSTANCE_ID" \
  --allocation-id "$EIP_ALLOC_ID"
```

## 7.3 Verificar

```bash
aws ec2 describe-addresses \
  --profile "$AWS_PROFILE" \
  --region "$AWS_REGION" \
  --allocation-ids "$EIP_ALLOC_ID" \
  --query 'Addresses[0].{PublicIp:PublicIp,InstanceId:InstanceId,AssociationId:AssociationId}' \
  --output table
```

---

# 8. Acceso SSH al host

Usuario esperado inicial en Ubuntu:
- `ubuntu`

```bash
ssh -i "${KEY_NAME}.pem" ubuntu@${EIP_PUBLIC_IP}
```

Si el acceso falla, validar:
- key correcta
- SG correcto
- subred pública
- route table con salida por Internet Gateway

---

# 9. Bootstrap Ubuntu ARM

Dentro de la instancia:

## 9.1 Base del host

```bash
sudo apt-get update
sudo apt-get install -y ca-certificates curl gnupg git jq unzip htop
```

## 9.2 Docker Engine + Compose plugin

```bash
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg

echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo $VERSION_CODENAME) stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
sudo systemctl enable docker
sudo systemctl start docker
sudo usermod -aG docker ubuntu
```

Cerrar y volver a entrar por SSH para que tome el grupo `docker`.

## 9.3 Verificar Docker

```bash
docker version
docker compose version
docker info >/dev/null && echo OK
```

## 9.4 Crear árbol operativo

```bash
sudo mkdir -p /opt/miwayki-platform
sudo mkdir -p /var/opt/miwayki-dify
sudo mkdir -p /var/opt/miwayki-secrets
sudo mkdir -p /var/log/miwayki
sudo chown -R ubuntu:ubuntu /opt/miwayki-platform /var/opt/miwayki-dify /var/log/miwayki
```

---

# 10. Entrada del código al host

## 10.1 Preparación local

En tu Mac, desde el repo:

```bash
git status
git checkout -b aws-phase1-trial
```

Agregar/committear el estado exacto que quieres desplegar.

```bash
git add .
git commit -m "AWS phase1 trial baseline"
git push -u origin aws-phase1-trial
```

## 10.2 Clone en EC2

Dentro de la EC2:

```bash
cd /opt/miwayki-platform
git clone <REPO_URL> app
cd app
git checkout aws-phase1-trial
```

## 10.3 Verificación

```bash
git rev-parse --short HEAD
git status
```

---

# 11. Secrets y archivos `.env`

## Regla
Los secretos no se suben al repositorio. Se crean en la EC2.

## Archivos esperados
Como mínimo:
- `compose/.env`
- `compose/.env.bridge`
- `compose/.env.chatwoot`
- cualquier `.env` de Dify que ya uses en local

## Método recomendado
Crear los archivos con `nano`, `cat > file <<EOF`, o copiarlos por `scp` si ya los tienes localmente preparados.

## Variables mínimas críticas
- `CHATWOOT_API_TOKEN`
- `CHATWOOT_WEBHOOK_SECRET`
- `DIFY_API_KEY`
- URL base y puertos correctos para AWS
- secretos del modelo/proveedor que Dify usa en este trial

---

# 12. Levantamiento del core

## Orden
1. Postgres + Redis
2. Chatwoot
3. Bridge
4. servicios auxiliares si el árbol del proyecto lo requiere

## Nota operativa
Todos los `docker compose` del trial se ejecutan **dentro de la EC2**.

## Comandos de referencia
Desde `/opt/miwayki-platform/app`:

```bash
./miwayki-compose.sh up -d
```

Si el proyecto exige `--build` en el bridge para reflejar el commit desplegado:

```bash
./miwayki-compose.sh up -d --build bridge
```

## Validación del core

```bash
docker ps
curl -sS http://127.0.0.1:8000/health | jq .
```

---

# 13. Chatwoot

## Objetivo
Dejar la bandeja humana operativa en AWS.

## Tareas
1. Confirmar que Chatwoot web y worker están arriba.
2. Si es primera subida, correr preparación DB según el flujo ya usado por tu compose.
3. Completar onboarding inicial.
4. Crear inbox web.
5. Obtener:
   - website token
   - API token administrativo
6. Configurar webhook hacia el Bridge.

## Validación
- acceder por navegador a la URL pública del host
- entrar a Chatwoot
- crear inbox web
- ver conversaciones entrantes

---

# 14. Bridge

## Objetivo
Validar la capa de integración ya cerrada en fase básica local.

## Checks obligatorios

```bash
curl -sS http://127.0.0.1:8000/health | jq .
curl -sS http://127.0.0.1:8000/health/dify | jq .
```

## Criterio
- `bridge_build` correcto
- Dify `reachable: true` cuando ya esté levantado

---

# 15. Dify como stack separado

## Regla
Dify **no** se embebe en el compose del core.

## Ubicación sugerida
`/var/opt/miwayki-dify/`

## Tareas
1. copiar o clonar el árbol de Dify/overlay necesario
2. levantar compose propio de Dify
3. unir Dify a la red compartida del proyecto
4. verificar que el Bridge lo consume por hostname interno `http://api:5001/v1`

## Nota importante
No se usará `127.0.0.1` para el consumo del API interno desde el Bridge.

## Validaciones
- health de Dify desde el host o desde red interna
- `curl /health/dify` del Bridge

---

# 16. Exposición pública temporal

## Regla del trial
Para esta prueba del día, el objetivo no es TLS final sino **bring-up + E2E técnico**.

## Decisión
Se usará:
- Elastic IP
- HTTP temporal controlado

## Observación
Dify no bloquea el arranque por no tener dominio final en este trial. Si una variable pública lo exige, puede usar IP pública o DNS público de EC2 según la configuración concreta del stack.

---

# 17. Validación E2E mínima en AWS

## Secuencia
1. abrir Chatwoot y/o widget según la exposición temporal montada
2. enviar mensaje inicial
3. verificar que entra al inbox
4. verificar que el webhook llama al Bridge
5. verificar que el Bridge llama a Dify
6. verificar que el Bridge publica la respuesta en el mismo hilo
7. verificar atributos de conversación
8. si la configuración del trial lo permite, validar contacto y etiquetas

## Estado mínimo de éxito
- respuesta de IA visible en el hilo
- `/health` correcto
- `/health/dify` correcto
- Chatwoot funcional
- Bridge funcional
- Dify funcional

---

# 18. Comandos útiles de operación en EC2

## Estado de contenedores

```bash
docker ps
docker compose ps
```

## Logs del bridge

```bash
docker logs --tail 200 -f miwayki-bridge
```

## Logs de Chatwoot

```bash
docker logs --tail 200 -f <chatwoot-web-container>
```

## Logs de Dify

```bash
docker compose -f <DIFY_COMPOSE_FILE> logs --tail 200 -f
```

---

# 19. Criterio de éxito del trial

La prueba se considera exitosa si se logra:
- SSH estable a la EC2
- Elastic IP asociada
- core arriba
- Dify arriba como stack separado
- Bridge alcanzando Dify por red interna
- Chatwoot operativo
- mensaje E2E de prueba funcionando
- runbook suficientemente claro para repetir la subida

---

# 20. Cierre del día

Como este entorno no quedará en producción:

## Si la prueba salió bien
1. guardar evidencias
2. guardar `instance-id`, `public-ip`, `allocation-id`, `sg-id`, commit desplegado
3. exportar notas y ajustes reales hechos en EC2
4. detener la instancia si se termina la jornada

```bash
aws ec2 stop-instances \
  --profile "$AWS_PROFILE" \
  --region "$AWS_REGION" \
  --instance-ids "$INSTANCE_ID"
```

## Si ya no se necesita la Elastic IP
Se puede liberar al final para evitar costos residuales:

```bash
aws ec2 disassociate-address \
  --profile "$AWS_PROFILE" \
  --region "$AWS_REGION" \
  --association-id <ASSOCIATION_ID>

aws ec2 release-address \
  --profile "$AWS_PROFILE" \
  --region "$AWS_REGION" \
  --allocation-id "$EIP_ALLOC_ID"
```

---

# 21. Riesgos conocidos y mitigaciones

## Riesgo: mezclar cambio de infraestructura y cambio de modelo
Mitigación: no usar Bedrock todavía.

## Riesgo: drift entre local y AWS
Mitigación: rama dedicada + clone limpio.

## Riesgo: exponer servicios internos
Mitigación: SG mínimo y sin `5432/6379` públicos.

## Riesgo: correr compose desde el lugar equivocado
Mitigación: todos los compose se ejecutan en la EC2 real.

## Riesgo: perder tiempo con DNS/TLS final
Mitigación: HTTP temporal controlado para el trial.

---

# 22. Primer bloque de ejecución real

Al arrancar la sesión operativa, el orden será este:

1. validar `aws sts get-caller-identity`
2. obtener tu IP pública (`MYIP`)
3. listar VPCs y subredes
4. crear key pair nueva
5. crear SG dedicado
6. resolver AMI Ubuntu ARM
7. lanzar `m7g.xlarge`
8. asociar Elastic IP
9. entrar por SSH
10. bootstrap Ubuntu + Docker
11. subir repo por Git
12. cargar `.env`
13. levantar core
14. levantar Dify
15. validar `/health`, `/health/dify` y E2E

