import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts'
import client from '../api/client'

interface Measurement {
  time: string
  value: number
}

export default function CardDetail() {
  const { cardSerial } = useParams()
  const [measurements, setMeasurements] = useState<Measurement[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const fetchMeasurements = async () => {
      if (!cardSerial) return
      
      try {
        const response = await client.get(`/cards/${cardSerial}/measurements`)
        const data = response.data.measurements || []
        setMeasurements(data.map((m: any) => ({
          time: new Date(m.time).toLocaleTimeString(),
          value: m.value
        })))
      } catch (error) {
        console.error('Error fetching measurements:', error)
      } finally {
        setLoading(false)
      }
    }

    fetchMeasurements()
    const interval = setInterval(fetchMeasurements, 30000)
    return () => clearInterval(interval)
  }, [cardSerial])

  if (loading) {
    return <div className="text-center py-12">Loading...</div>
  }

  return (
    <div className="px-4 py-6 sm:px-0">
      <h1 className="text-3xl font-bold text-gray-900 mb-6">Card: {cardSerial}</h1>
      
      <div className="bg-white shadow rounded-lg p-6">
        <h2 className="text-xl font-semibold text-gray-900 mb-4">Measurements</h2>
        {measurements.length === 0 ? (
          <p className="text-gray-500">No measurements available</p>
        ) : (
          <ResponsiveContainer width="100%" height={400}>
            <LineChart data={measurements}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="time" />
              <YAxis />
              <Tooltip />
              <Legend />
              <Line type="monotone" dataKey="value" stroke="#8884d8" />
            </LineChart>
          </ResponsiveContainer>
        )}
      </div>
    </div>
  )
}




