import { useEffect, useState } from 'react'
import client from '../api/client'
import { getCardStatus } from '../utils/cardStatus'

interface Site {
  site_id: string
  name: string
}

interface Alarm {
  alarmId: string
  severity: string
  description: string
  cardSerial: string
  locationSite: string
  triggeredAt: string
}

interface Card {
  cardSerial: string
  cardModel: string
  lastUpdated: string | null
}

export default function Dashboard() {
  const [sites, setSites] = useState<Site[]>([])
  const [alarms, setAlarms] = useState<Alarm[]>([])
  const [cards, setCards] = useState<Card[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [sitesRes, alarmsRes, cardsRes] = await Promise.all([
          client.get('/sites'),
          client.get('/alarms?status=ACTIVE&limit=10'),
          client.get('/cards'),
        ])
        setSites(sitesRes.data.sites || [])
        setAlarms(alarmsRes.data.alarms || [])
        setCards(cardsRes.data.cards || [])
      } catch (error) {
        console.error('Error fetching data:', error)
      } finally {
        setLoading(false)
      }
    }

    fetchData()
    const interval = setInterval(fetchData, 30000) // Refresh every 30 seconds
    return () => clearInterval(interval)
  }, [])

  if (loading) {
    return <div className="text-center py-12">Loading...</div>
  }

  // Calculate latest collection time
  const latestCollectionTime = cards.reduce((max: number, card: Card) => {
    if (!card.lastUpdated) return max
    const time = new Date(card.lastUpdated).getTime()
    return time > max ? time : max
  }, 0)

  const cardStats = cards.reduce(
    (acc: { online: number; offline: number }, card: Card) => {
      const { status } = getCardStatus(card, latestCollectionTime)
      if (status === 'ONLINE') acc.online++
      else if (status === 'OFFLINE') acc.offline++
      return acc
    },
    { online: 0, offline: 0 }
  )

  return (
    <div className="px-4 py-6 sm:px-0">
      <h1 className="text-3xl font-bold text-gray-900 mb-6">Dashboard</h1>

      <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-3 mb-6">
        <div className="bg-white overflow-hidden shadow rounded-lg">
          <div className="p-5">
            <div className="flex items-center">
              <div className="flex-shrink-0">
                <div className="text-2xl font-bold text-gray-900">{sites.length}</div>
              </div>
              <div className="ml-5 w-0 flex-1">
                <dl>
                  <dt className="text-sm font-medium text-gray-500 truncate">Sites</dt>
                </dl>
              </div>
            </div>
          </div>
        </div>

        <div className="bg-white overflow-hidden shadow rounded-lg">
          <div className="p-5">
            <div className="flex items-center">
              <div className="flex-shrink-0">
                <div className="flex flex-col">
                  <span className="text-lg font-bold text-green-600">{cardStats.online} Online</span>
                  <span className="text-lg font-bold text-red-600">{cardStats.offline} Offline</span>
                </div>
              </div>
              <div className="ml-5 w-0 flex-1">
                <dl>
                  <dt className="text-sm font-medium text-gray-500 truncate">Cards Status</dt>
                </dl>
              </div>
            </div>
          </div>
        </div>

        <div className="bg-white overflow-hidden shadow rounded-lg">
          <div className="p-5">
            <div className="flex items-center">
              <div className="flex-shrink-0">
                <div className="flex flex-col">
                  <span className="text-lg font-bold text-gray-900">{alarms.length} Total</span>
                  <span className="text-sm font-bold text-red-600">
                    {alarms.filter(a => a.severity === 'CRITICAL').length} Critical
                  </span>
                  <span className="text-sm font-bold text-orange-600">
                    {alarms.filter(a => a.severity === 'MAJOR').length} Major
                  </span>
                </div>
              </div>
              <div className="ml-5 w-0 flex-1">
                <dl>
                  <dt className="text-sm font-medium text-gray-500 truncate">Active Alarms</dt>
                </dl>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}




