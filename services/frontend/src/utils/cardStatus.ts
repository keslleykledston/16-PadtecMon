export interface CardStatusInput {
    cardModel: string
    lastUpdated: string | null
}

export interface CardStatusResult {
    status: 'ONLINE' | 'OFFLINE' | 'PASSIVE' | 'UNKNOWN'
    color: string
}

export const getCardStatus = (card: CardStatusInput, latestCollectionTime: number): CardStatusResult => {
    // MUX_DEMUX exception
    if (card.cardModel && card.cardModel.includes('MUX_DEMUX')) {
        return { status: 'PASSIVE', color: 'bg-blue-100 text-blue-800' }
    }

    if (!card.lastUpdated) {
        return { status: 'UNKNOWN', color: 'bg-gray-100 text-gray-800' }
    }

    const cardTime = new Date(card.lastUpdated).getTime()
    // 2 minutes in milliseconds
    const twoMinutes = 2 * 60 * 1000

    // Check if card is outdated relative to the latest collection
    if (latestCollectionTime - cardTime > twoMinutes) {
        return { status: 'OFFLINE', color: 'bg-red-100 text-red-800' }
    }

    return { status: 'ONLINE', color: 'bg-green-100 text-green-800' }
}
