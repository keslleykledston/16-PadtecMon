import { useEffect, useState } from 'react'
import { CheckCircleIcon, XCircleIcon, ArrowPathIcon } from '@heroicons/react/24/outline'
import client from '../api/client'

interface Config {
  padtecApiUrl: string
  padtecApiToken: string
  collectIntervalCritical: number
  collectIntervalNormal: number
}

interface ApiStatus {
  connected: boolean
  message: string
  lastCheck?: string
}

export default function Config() {
  const [config, setConfig] = useState<Config>({
    padtecApiUrl: '',
    padtecApiToken: '',
    collectIntervalCritical: 30,
    collectIntervalNormal: 300
  })
  const [apiStatus, setApiStatus] = useState<ApiStatus>({
    connected: false,
    message: 'Não verificado'
  })
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [testing, setTesting] = useState(false)
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null)

  useEffect(() => {
    fetchConfig()
    checkStatus()

    const intervalId = setInterval(checkStatus, 5 * 60 * 1000) // 5 minutes

    return () => clearInterval(intervalId)
  }, [])

  const fetchConfig = async () => {
    try {
      const response = await client.get('/config')
      if (response.data) {
        setConfig(response.data)
      }
    } catch (error) {
      console.error('Error fetching config:', error)
    } finally {
      setLoading(false)
    }
  }

  const checkStatus = async () => {
    // Don't check if we are currently manually testing or saving
    if (testing || saving) return

    try {
      const response = await client.get('/config/padtec-status')
      setApiStatus({
        connected: response.data.connected,
        message: response.data.message,
        lastCheck: new Date().toLocaleString()
      })
    } catch (error: any) {
      console.error('Error checking API status:', error)
      // Don't overwrite error message if it was manually set recently?
      // Actually, we want to show the current status.
      setApiStatus(prev => ({
        ...prev,
        connected: false,
        message: 'Erro ao verificar status automaticamente',
        lastCheck: new Date().toLocaleString()
      }))
    }
  }

  const testConnection = async () => {
    setTesting(true)
    setApiStatus({ connected: false, message: 'Testando conexão...' })

    try {
      const response = await client.post('/config/test-connection', {
        padtecApiUrl: config.padtecApiUrl,
        padtecApiToken: config.padtecApiToken
      })

      setApiStatus({
        connected: response.data.connected,
        message: response.data.message,
        lastCheck: new Date().toLocaleString()
      })

      if (response.data.connected) {
        setMessage({ type: 'success', text: 'Conexão com API Padtec bem-sucedida!' })
      } else {
        setMessage({ type: 'error', text: response.data.message })
      }
    } catch (error: any) {
      setApiStatus({
        connected: false,
        message: error.response?.data?.message || 'Erro ao testar conexão',
        lastCheck: new Date().toLocaleString()
      })
      setMessage({ type: 'error', text: 'Erro ao testar conexão com a API Padtec' })
    } finally {
      setTesting(false)
      setTimeout(() => setMessage(null), 5000)
    }
  }

  const saveConfig = async () => {
    setSaving(true)
    setMessage(null)

    try {
      const response = await client.put('/config', config)

      if (response.data?.config) {
        setConfig({
          padtecApiUrl: response.data.config.padtecApiUrl,
          padtecApiToken: response.data.config.padtecApiToken,
          collectIntervalCritical: response.data.config.collectIntervalCritical,
          collectIntervalNormal: response.data.config.collectIntervalNormal,
        })
      }
      setMessage({ type: 'success', text: 'Configurações salvas com sucesso!' })

      // Reiniciar o collector para aplicar as novas configurações
      try {
        await client.post('/collector/restart')
      } catch (e) {
        console.warn('Não foi possível reiniciar o collector:', e)
      }
    } catch (error: any) {
      setMessage({
        type: 'error',
        text: error.response?.data?.message || 'Erro ao salvar configurações'
      })
    } finally {
      setSaving(false)
      setTimeout(() => setMessage(null), 5000)
    }
  }

  if (loading) {
    return <div className="text-center py-12">Carregando configurações...</div>
  }

  return (
    <div className="px-4 py-6 sm:px-0">
      <h1 className="text-3xl font-bold text-gray-900 mb-6">Configuração</h1>

      {message && (
        <div className={`mb-6 p-4 rounded-lg ${message.type === 'success'
            ? 'bg-green-50 text-green-800 border border-green-200'
            : 'bg-red-50 text-red-800 border border-red-200'
          }`}>
          {message.text}
        </div>
      )}

      {/* Status da API Padtec */}
      <div className="bg-white shadow rounded-lg mb-6">
        <div className="px-4 py-5 sm:p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-medium text-gray-900">Status da API Padtec</h2>
            <button
              onClick={testConnection}
              disabled={testing}
              className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <ArrowPathIcon className={`h-4 w-4 mr-2 ${testing ? 'animate-spin' : ''}`} />
              {testing ? 'Testando...' : 'Testar Conexão'}
            </button>
          </div>

          <div className="flex items-center space-x-3">
            {apiStatus.connected ? (
              <CheckCircleIcon className="h-6 w-6 text-green-500" />
            ) : (
              <XCircleIcon className="h-6 w-6 text-red-500" />
            )}
            <div>
              <p className={`text-sm font-medium ${apiStatus.connected ? 'text-green-700' : 'text-red-700'
                }`}>
                {apiStatus.connected ? 'Conectado' : 'Desconectado'}
              </p>
              <p className="text-sm text-gray-500">{apiStatus.message}</p>
              {apiStatus.lastCheck && (
                <p className="text-xs text-gray-400 mt-1">
                  Última verificação: {apiStatus.lastCheck}
                </p>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Configurações da API Padtec */}
      <div className="bg-white shadow rounded-lg mb-6">
        <div className="px-4 py-5 sm:p-6">
          <h2 className="text-lg font-medium text-gray-900 mb-4">Configurações da API Padtec</h2>

          <div className="space-y-4">
            <div>
              <label htmlFor="apiUrl" className="block text-sm font-medium text-gray-700">
                URL da API Padtec
              </label>
              <input
                type="text"
                id="apiUrl"
                value={config.padtecApiUrl}
                onChange={(e) => setConfig({ ...config, padtecApiUrl: e.target.value })}
                className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm px-3 py-2 border"
                placeholder="http://172.30.0.21:8181/nms-api/"
              />
            </div>

            <div>
              <label htmlFor="apiToken" className="block text-sm font-medium text-gray-700">
                Token da API Padtec
              </label>
              <input
                type="password"
                id="apiToken"
                value={config.padtecApiToken}
                onChange={(e) => setConfig({ ...config, padtecApiToken: e.target.value })}
                className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm px-3 py-2 border"
                placeholder="Bearer token"
              />
              <p className="mt-1 text-xs text-gray-500">
                O token será armazenado de forma segura
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Configurações de Coleta */}
      <div className="bg-white shadow rounded-lg mb-6">
        <div className="px-4 py-5 sm:p-6">
          <h2 className="text-lg font-medium text-gray-900 mb-4">Intervalos de Coleta</h2>

          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <div>
              <label htmlFor="intervalCritical" className="block text-sm font-medium text-gray-700">
                Intervalo Crítico (segundos)
              </label>
              <input
                type="number"
                id="intervalCritical"
                min="10"
                max="300"
                value={config.collectIntervalCritical}
                onChange={(e) => setConfig({ ...config, collectIntervalCritical: parseInt(e.target.value) || 30 })}
                className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm px-3 py-2 border"
              />
              <p className="mt-1 text-xs text-gray-500">
                Medições críticas (Pump Power, OSNR). Recomendado: 30-60 segundos
              </p>
            </div>

            <div>
              <label htmlFor="intervalNormal" className="block text-sm font-medium text-gray-700">
                Intervalo Normal (segundos)
              </label>
              <input
                type="number"
                id="intervalNormal"
                min="60"
                max="3600"
                value={config.collectIntervalNormal}
                onChange={(e) => setConfig({ ...config, collectIntervalNormal: parseInt(e.target.value) || 300 })}
                className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm px-3 py-2 border"
              />
              <p className="mt-1 text-xs text-gray-500">
                Medições normais. Recomendado: 300 segundos (5 minutos)
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Botão Salvar */}
      <div className="flex justify-end">
        <button
          onClick={saveConfig}
          disabled={saving}
          className="inline-flex items-center px-6 py-3 border border-transparent text-base font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {saving ? 'Salvando...' : 'Salvar Configurações'}
        </button>
      </div>
    </div>
  )
}

