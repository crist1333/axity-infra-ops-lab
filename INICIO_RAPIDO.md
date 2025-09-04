# 🚀 AXITY LAB - INICIO RÁPIDO

## ⚡ Ejecución Inmediata de Casos Prácticos

### 🎯 Para Ejecutivos y Stakeholders

```bash
# Ejecutar demostración completa (45 minutos)
./scripts/ejecutar_casos_axity.sh
# Seleccionar opción 4: "EJECUTAR TODOS LOS CASOS"
```

### 🔍 Para Revisión Individual

```bash
# Caso 1: E-commerce Crítico (10 minutos)
./scripts/caso_1_ecommerce.sh

# Caso 2: Banking Compliance (15 minutos) 
./scripts/caso_2_banking.sh

# Caso 3: Retail Multinivel (12 minutos)
./scripts/caso_3_retail.sh
```

### 🌐 Acceso a Dashboards

- **GLPI ITSM**: http://localhost:8080 (`glpi` / `glpi`)
- **Prometheus**: http://localhost:9090
- **AlertManager**: http://localhost:9093
- **Demo App**: http://localhost:8000
- **API Webhook**: http://localhost:5000

### 📊 Verificar Sistema

```bash
# Health check completo
./scripts/ejecutar_casos_axity.sh
# Seleccionar opción 5: "VERIFICAR SISTEMA"
```

### 📋 Reportes Generados

Los casos prácticos generan automáticamente:

- **Reportes JSON**: `reports/`
- **Dashboards**: `dashboards/`
- **Métricas de negocio**: ROI, ahorro costos, eficiencia

### ⚠️ Prerrequisitos Mínimos

✅ **Docker Desktop**: Ejecutándose  
✅ **Servicios Lab**: Todos los contenedores activos  
✅ **Puertos**: 5000, 8000, 8080, 9090, 9093 disponibles

### 🆘 Solución de Problemas

```bash
# Si algún servicio no responde:
docker compose -f docker-compose.glpi.yml restart
cd infra/monitoring && docker compose restart

# Verificar logs:
docker logs glpi-app
docker logs axity-prometheus
```

### 🎉 Resultado Esperado

Al finalizar tendrás:
- ✅ 3 casos prácticos ejecutados exitosamente
- 📊 Reportes con métricas cuantificables
- 💰 Análisis de ROI y valor agregado  
- 🎯 Demostración completa de capacidades Axity

---

**🏢 Para más información consulte el [README-DEFINITIVO.md](README-DEFINITIVO.md)**