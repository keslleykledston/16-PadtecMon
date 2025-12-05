import { useEffect, useState } from 'react'
import client from '../api/client'

interface Alarm {
  alarmId: string
  alarmType: string
  severity: string
  cardSerial: string
  locationSite: string
  description: string
  triggeredAt: string
  clearedAt: string | null
  status: string
  cardModel?: string
  cardName?: string
}

export default function Alarms() {
  const [alarms, setAlarms] = useState<Alarm[]>([])
  const [loading, setLoading] = useState(true)
  const [filter, setFilter] = useState<string>('ALL')

  const [searchTerm, setSearchTerm] = useState('')

  useEffect(() => {
    const fetchAlarms = async () => {
      try {
        const params: { limit: number; status?: string } = { limit: 100 }
        // Default to ACTIVE alarms only
        if (filter === 'ALL') {
          params.status = 'ACTIVE'
        } else {
          params.status = filter
        }
        const response = await client.get('/alarms', { params })
        setAlarms(response.data.alarms || [])
      } catch (error) {
        console.error('Error fetching alarms:', error)
      } finally {
        setLoading(false)
      }
    }

    fetchAlarms()
    const interval = setInterval(fetchAlarms, 15000)
    return () => clearInterval(interval)
  }, [filter])

  const handleAcknowledge = async (alarmId: string) => {
    try {
      await client.post(`/alarms/${alarmId}/acknowledge`)
      setAlarms(alarms.map(a => a.alarmId === alarmId ? { ...a, status: 'ACKNOWLEDGED' } : a))
    } catch (error) {
      console.error('Error acknowledging alarm:', error)
    }
  }

  const getSeverityOrder = (severity: string): number => {
    switch (severity) {
      case 'CRITICAL': return 0
      case 'MAJOR': return 1
      case 'MINOR': return 2
      case 'WARNING': return 3
      default: return 4
    }
  }

  const filteredAlarms = alarms
    .filter(alarm => {
      const search = searchTerm.toLowerCase()
      return (
        alarm.description.toLowerCase().includes(search) ||
        alarm.cardSerial.toLowerCase().includes(search) ||
        alarm.locationSite.toLowerCase().includes(search)
      )
    })
    .sort((a, b) => getSeverityOrder(a.severity) - getSeverityOrder(b.severity))

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'CRITICAL':
        return 'bg-red-100 text-red-800'
      case 'MAJOR':
        return 'bg-orange-100 text-orange-800'
      case 'MINOR':
        return 'bg-yellow-100 text-yellow-800'
      default:
        return 'bg-gray-100 text-gray-800'
    }
  }

  if (loading) {
    return <div className="text-center py-12">Loading...</div>
  }

  return (
    <div className="px-4 py-6 sm:px-0">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-3xl font-bold text-gray-900">Alarms</h1>
        <div className="flex space-x-4">
          <input
            type="text"
            placeholder="Search by Description, Serial, Site..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="border border-gray-300 rounded-md px-3 py-2 w-64"
          />
          <select
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
            className="border border-gray-300 rounded-md px-3 py-2"
          >
            <option value="ALL">All Status</option>
            <option value="ACTIVE">Active</option>
            <option value="ACKNOWLEDGED">Acknowledged</option>
            <option value="CLEARED">Cleared</option>
          </select>
        </div>
      </div>

      <div className="bg-white shadow rounded-lg overflow-hidden">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Severity
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Description
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Card / Site
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Triggered
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Actions
              </th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {filteredAlarms.map((alarm) => (
              <tr key={alarm.alarmId}>
                <td className="px-6 py-4 whitespace-nowrap">
                  <span className={`px-2 inline-flex text-xs leading-5 font-semibold rounded-full ${getSeverityColor(alarm.severity)}`}>
                    {alarm.severity}
                  </span>
                </td>
                <td className="px-6 py-4 text-sm text-gray-900">{alarm.description}</td>
                <td className="px-6 py-4 text-sm">
                  <div className="text-gray-900">
                    {alarm.cardName || `${alarm.locationSite}-[${alarm.cardSerial}]-UNKNOWN`}
                  </div>
                  <div className="text-xs text-gray-500 italic">
                    {alarm.locationSite}
                  </div>
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                  {new Date(alarm.triggeredAt).toLocaleString()}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm">
                  {alarm.status === 'ACTIVE' && (
                    <button
                      onClick={() => handleAcknowledge(alarm.alarmId)}
                      className="text-blue-600 hover:text-blue-900"
                    >
                      Acknowledge
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}




