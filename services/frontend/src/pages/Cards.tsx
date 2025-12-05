import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import client from '../api/client'

import { getCardStatus } from '../utils/cardStatus'

interface Card {
  cardSerial: string
  cardPart: string
  cardFamily: string
  cardModel: string
  locationSite: string
  status: string
  lastUpdated: string | null
}

interface Measurement {
  measureKey: string
  measureName: string
  measureValue: number
  measureUnit: string
  measureGroup: string
  time: string
}

type SortKey = keyof Card

export default function Cards() {
  const [cards, setCards] = useState<Card[]>([])
  const [loading, setLoading] = useState(true)
  const [searchTerm, setSearchTerm] = useState('')
  const [syncing, setSyncing] = useState(false)
  const [sortConfig, setSortConfig] = useState<{ key: SortKey; direction: 'asc' | 'desc' } | null>(null)
  const [selectedCard, setSelectedCard] = useState<Card | null>(null)
  const [measurements, setMeasurements] = useState<Measurement[]>([])
  const [loadingMeasurements, setLoadingMeasurements] = useState(false)

  const fetchCards = async () => {
    try {
      setLoading(true)
      const response = await client.get('/cards')
      setCards(response.data.cards || [])
    } catch (error) {
      console.error('Error fetching cards:', error)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchCards()
  }, [])

  const handleSync = async () => {
    try {
      setSyncing(true)
      await client.post('/sites/sync')
      await fetchCards()
    } catch (error) {
      console.error('Error syncing cards:', error)
      alert('Failed to sync cards')
    } finally {
      setSyncing(false)
    }
  }

  const handleSort = (key: SortKey) => {
    let direction: 'asc' | 'desc' = 'asc'
    if (sortConfig && sortConfig.key === key && sortConfig.direction === 'asc') {
      direction = 'desc'
    }
    setSortConfig({ key, direction })
  }

  const handleShowMetrics = async (card: Card) => {
    setSelectedCard(card)
    setLoadingMeasurements(true)
    try {
      const response = await client.get(`/cards/${card.cardSerial}/measurements/latest`)
      setMeasurements(response.data.measurements || [])
    } catch (error) {
      console.error('Error fetching measurements:', error)
      setMeasurements([])
    } finally {
      setLoadingMeasurements(false)
    }
  }

  const handleCloseModal = () => {
    setSelectedCard(null)
    setMeasurements([])
  }

  // Calculate latest collection time
  const latestCollectionTime = cards.reduce((max, card) => {
    if (!card.lastUpdated) return max
    const time = new Date(card.lastUpdated).getTime()
    return time > max ? time : max
  }, 0)

  const sortedCards = [...cards].sort((a, b) => {
    if (!sortConfig) return 0

    const aValue = a[sortConfig.key]
    const bValue = b[sortConfig.key]

    if (aValue === null || aValue === undefined) return 1
    if (bValue === null || bValue === undefined) return -1

    if (aValue < bValue) {
      return sortConfig.direction === 'asc' ? -1 : 1
    }
    if (aValue > bValue) {
      return sortConfig.direction === 'asc' ? 1 : -1
    }
    return 0
  })

  const filteredCards = sortedCards.filter(card => {
    const search = searchTerm.toLowerCase()
    return (
      card.cardSerial.toLowerCase().includes(search) ||
      card.cardModel.toLowerCase().includes(search) ||
      card.locationSite.toLowerCase().includes(search) ||
      card.cardPart.toLowerCase().includes(search)
    )
  })

  if (loading && cards.length === 0) {
    return <div className="text-center py-12">Loading...</div>
  }

  const renderSortIcon = (key: SortKey) => {
    if (sortConfig?.key !== key) return null
    return sortConfig.direction === 'asc' ? ' ↑' : ' ↓'
  }

  return (
    <div className="px-4 py-6 sm:px-0">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-3xl font-bold text-gray-900">Cards</h1>
        <div className="flex space-x-4">
          <input
            type="text"
            placeholder="Search by Serial, Model, Site..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="border border-gray-300 rounded-md px-3 py-2"
          />
          <button
            onClick={handleSync}
            disabled={syncing}
            className={`inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 ${syncing ? 'opacity-50 cursor-not-allowed' : ''}`}
          >
            {syncing ? 'Syncing...' : 'Sync Cards'}
          </button>
        </div>
      </div>
      <div className="bg-white shadow rounded-lg overflow-hidden">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th
                className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
                onClick={() => handleSort('cardSerial')}
              >
                Serial {renderSortIcon('cardSerial')}
              </th>
              <th
                className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
                onClick={() => handleSort('cardPart')}
              >
                Part {renderSortIcon('cardPart')}
              </th>
              <th
                className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
                onClick={() => handleSort('cardFamily')}
              >
                Family {renderSortIcon('cardFamily')}
              </th>
              <th
                className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
                onClick={() => handleSort('cardModel')}
              >
                Model {renderSortIcon('cardModel')}
              </th>
              <th
                className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
                onClick={() => handleSort('locationSite')}
              >
                Site {renderSortIcon('locationSite')}
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Status
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Actions
              </th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {filteredCards.map((card) => {
              const { status, color } = getCardStatus(card, latestCollectionTime)
              return (
                <tr key={card.cardSerial} className="hover:bg-gray-50">
                  <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-blue-600">
                    <Link to={`/cards/${card.cardSerial}`}>{card.cardSerial}</Link>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                    {card.cardPart}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    {card.cardFamily}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    {card.cardModel}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    {card.locationSite}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span className={`px-2 inline-flex text-xs leading-5 font-semibold rounded-full ${color}`}>
                      {status}
                    </span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm">
                    <button
                      onClick={() => handleShowMetrics(card)}
                      className="text-indigo-600 hover:text-indigo-900"
                      title="View Metrics"
                    >
                      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                      </svg>
                    </button>
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>

      {/* Metrics Modal */}
      {selectedCard && (
        <div className="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50" onClick={handleCloseModal}>
          <div className="relative top-20 mx-auto p-5 border w-11/12 max-w-4xl shadow-lg rounded-md bg-white" onClick={(e) => e.stopPropagation()}>
            <div className="flex justify-between items-center mb-4">
              <h3 className="text-lg font-medium text-gray-900">
                Device Metrics - {selectedCard.cardSerial}
              </h3>
              <button
                onClick={handleCloseModal}
                className="text-gray-400 hover:text-gray-500"
              >
                <svg className="h-6 w-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>

            <div className="mb-4 text-sm text-gray-600">
              <p><strong>Model:</strong> {selectedCard.cardModel}</p>
              <p><strong>Site:</strong> {selectedCard.locationSite}</p>
              <p><strong>Part:</strong> {selectedCard.cardPart}</p>
            </div>

            {loadingMeasurements ? (
              <div className="text-center py-8">
                <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600"></div>
                <p className="mt-2 text-gray-600">Loading measurements...</p>
              </div>
            ) : measurements.length === 0 ? (
              <div className="text-center py-8 text-gray-500">
                No measurements available for this device
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-gray-200">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Measure</th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Value</th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Unit</th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Group</th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Time</th>
                    </tr>
                  </thead>
                  <tbody className="bg-white divide-y divide-gray-200">
                    {measurements.map((measurement, index) => (
                      <tr key={index} className="hover:bg-gray-50">
                        <td className="px-4 py-3 text-sm text-gray-900">{measurement.measureName}</td>
                        <td className="px-4 py-3 text-sm font-medium text-gray-900">
                          {measurement.measureValue?.toFixed(2) || 'N/A'}
                        </td>
                        <td className="px-4 py-3 text-sm text-gray-500">{measurement.measureUnit}</td>
                        <td className="px-4 py-3 text-sm text-gray-500">{measurement.measureGroup}</td>
                        <td className="px-4 py-3 text-sm text-gray-500">
                          {new Date(measurement.time).toLocaleString()}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}




