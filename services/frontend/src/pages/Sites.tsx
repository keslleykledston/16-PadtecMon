import { useEffect, useState } from 'react'
import client from '../api/client'

interface Site {
  site_id: string
  name: string
}

export default function Sites() {
  const [sites, setSites] = useState<Site[]>([])
  const [loading, setLoading] = useState(true)
  const [syncing, setSyncing] = useState(false)

  const [searchTerm, setSearchTerm] = useState('')

  const fetchSites = async () => {
    try {
      setLoading(true)
      const response = await client.get('/sites')
      setSites(response.data.sites || [])
    } catch (error) {
      console.error('Error fetching sites:', error)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchSites()
  }, [])

  const handleSync = async () => {
    try {
      setSyncing(true)
      const response = await client.post('/sites/sync')
      if (response.data.sites) {
        setSites(response.data.sites)
      } else {
        await fetchSites()
      }
    } catch (error) {
      console.error('Error syncing sites:', error)
      alert('Failed to sync sites')
    } finally {
      setSyncing(false)
    }
  }

  const filteredSites = sites.filter(site => {
    const search = searchTerm.toLowerCase()
    return (
      site.name.toLowerCase().includes(search) ||
      site.site_id.toLowerCase().includes(search)
    )
  })

  if (loading && sites.length === 0) {
    return <div className="text-center py-12">Loading...</div>
  }

  return (
    <div className="px-4 py-6 sm:px-0">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-3xl font-bold text-gray-900">Sites</h1>
        <div className="flex space-x-4">
          <input
            type="text"
            placeholder="Search by Name or ID..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="border border-gray-300 rounded-md px-3 py-2"
          />
          <button
            onClick={handleSync}
            disabled={syncing}
            className={`inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 ${syncing ? 'opacity-50 cursor-not-allowed' : ''
              }`}
          >
            {syncing ? (
              <>
                <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
                Syncing...
              </>
            ) : (
              'Sync Sites'
            )}
          </button>
        </div>
      </div>
      <div className="bg-white shadow rounded-lg">
        <div className="px-4 py-5 sm:p-6">
          {filteredSites.length === 0 ? (
            <p className="text-gray-500">No sites found.</p>
          ) : (
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {filteredSites.map((site) => (
                <div key={site.site_id} className="border rounded-lg p-4 hover:shadow-md transition-shadow">
                  <h3 className="text-lg font-medium text-gray-900">{site.name}</h3>
                  <p className="text-sm text-gray-500 mt-1">Site ID: {site.site_id}</p>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}




