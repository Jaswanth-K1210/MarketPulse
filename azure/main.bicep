// MarketPulse-X — Azure infrastructure
// Resources: Container Apps Environment, Python backend CA, .NET gateway CA,
//            Storage Account (reports), Log Analytics workspace, App Insights

targetScope = 'resourceGroup'

@description('Deployment environment')
@allowed(['dev', 'staging', 'prod'])
param env string = 'prod'

@description('Azure region')
param location string = resourceGroup().location

@description('Python FastAPI backend container image (e.g. ghcr.io/org/marketpulse-backend:latest)')
param backendImage string

@description('.NET gateway container image (e.g. ghcr.io/org/marketpulse-gateway:latest)')
param gatewayImage string

@description('OpenAI API key for the backend')
@secure()
param openaiApiKey string

@description('MongoDB Atlas connection string')
@secure()
param mongodbUri string

@description('JWT secret key')
@secure()
param jwtSecret string

var prefix = 'mktpulse-${env}'
var tags   = { project: 'MarketPulse-X', env: env }

// ── Log Analytics ─────────────────────────────────────────────────────────────

resource logAnalytics 'Microsoft.OperationalInsights/workspaces@2022-10-01' = {
  name: '${prefix}-logs'
  location: location
  tags: tags
  properties: {
    sku: { name: 'PerGB2018' }
    retentionInDays: 30
  }
}

// ── Application Insights ─────────────────────────────────────────────────────

resource appInsights 'Microsoft.Insights/components@2020-02-02' = {
  name: '${prefix}-ai'
  location: location
  kind: 'web'
  tags: tags
  properties: {
    Application_Type: 'web'
    WorkspaceResourceId: logAnalytics.id
  }
}

// ── Storage Account (report blobs) ───────────────────────────────────────────

resource storageAccount 'Microsoft.Storage/storageAccounts@2023-01-01' = {
  name: replace('${prefix}reports', '-', '')
  location: location
  sku: { name: 'Standard_LRS' }
  kind: 'StorageV2'
  tags: tags
  properties: {
    accessTier: 'Hot'
    allowBlobPublicAccess: false
    minimumTlsVersion: 'TLS1_2'
    supportsHttpsTrafficOnly: true
  }
}

resource blobService 'Microsoft.Storage/storageAccounts/blobServices@2023-01-01' = {
  parent: storageAccount
  name: 'default'
}

resource reportsContainer 'Microsoft.Storage/storageAccounts/blobServices/containers@2023-01-01' = {
  parent: blobService
  name: 'marketpulse-reports'
  properties: { publicAccess: 'None' }
}

// ── Container Apps Environment ────────────────────────────────────────────────

resource caEnv 'Microsoft.App/managedEnvironments@2023-05-01' = {
  name: '${prefix}-env'
  location: location
  tags: tags
  properties: {
    appLogsConfiguration: {
      destination: 'log-analytics'
      logAnalyticsConfiguration: {
        customerId: logAnalytics.properties.customerId
        sharedKey: logAnalytics.listKeys().primarySharedKey
      }
    }
  }
}

// ── Python FastAPI Backend ────────────────────────────────────────────────────

resource backendApp 'Microsoft.App/containerApps@2023-05-01' = {
  name: '${prefix}-backend'
  location: location
  tags: tags
  properties: {
    managedEnvironmentId: caEnv.id
    configuration: {
      ingress: {
        external: false
        targetPort: 8000
        transport: 'http'
      }
      secrets: [
        { name: 'openai-key',  value: openaiApiKey }
        { name: 'mongodb-uri', value: mongodbUri   }
        { name: 'jwt-secret',  value: jwtSecret    }
        { name: 'ai-conn-str', value: appInsights.properties.ConnectionString }
      ]
    }
    template: {
      containers: [
        {
          name: 'backend'
          image: backendImage
          resources: { cpu: json('0.5'), memory: '1Gi' }
          env: [
            { name: 'OPENAI_API_KEY',  secretRef: 'openai-key'  }
            { name: 'MONGODB_URI',     secretRef: 'mongodb-uri'  }
            { name: 'JWT_SECRET_KEY',  secretRef: 'jwt-secret'   }
            { name: 'APPLICATIONINSIGHTS_CONNECTION_STRING', secretRef: 'ai-conn-str' }
            { name: 'ENVIRONMENT',     value: env }
          ]
        }
      ]
      scale: { minReplicas: 1, maxReplicas: 5 }
    }
  }
}

// ── .NET Gateway ──────────────────────────────────────────────────────────────

resource gatewayApp 'Microsoft.App/containerApps@2023-05-01' = {
  name: '${prefix}-gateway'
  location: location
  tags: tags
  properties: {
    managedEnvironmentId: caEnv.id
    configuration: {
      ingress: {
        external: true
        targetPort: 5000
        transport: 'http'
        corsPolicy: {
          allowedOrigins: ['https://*.vercel.app', 'https://marketpulse.io']
          allowedMethods: ['GET', 'POST', 'OPTIONS']
          allowedHeaders: ['*']
        }
      }
      secrets: [
        { name: 'storage-conn-str', value: 'DefaultEndpointsProtocol=https;AccountName=${storageAccount.name};AccountKey=${storageAccount.listKeys().keys[0].value};EndpointSuffix=core.windows.net' }
        { name: 'ai-conn-str',      value: appInsights.properties.ConnectionString }
      ]
    }
    template: {
      containers: [
        {
          name: 'gateway'
          image: gatewayImage
          resources: { cpu: json('0.5'), memory: '1Gi' }
          env: [
            { name: 'PythonBackendUrl',               value: 'http://${backendApp.name}:8000' }
            { name: 'AzureStorageConnectionString',   secretRef: 'storage-conn-str' }
            { name: 'APPLICATIONINSIGHTS_CONNECTION_STRING', secretRef: 'ai-conn-str' }
            { name: 'ASPNETCORE_ENVIRONMENT',         value: env == 'prod' ? 'Production' : 'Staging' }
          ]
        }
      ]
      scale: { minReplicas: 1, maxReplicas: 3 }
    }
  }
}

// ── Outputs ───────────────────────────────────────────────────────────────────

output gatewayUrl          string = 'https://${gatewayApp.properties.configuration.ingress.fqdn}'
output storageAccountName  string = storageAccount.name
output appInsightsKey      string = appInsights.properties.InstrumentationKey
output logAnalyticsId      string = logAnalytics.id
