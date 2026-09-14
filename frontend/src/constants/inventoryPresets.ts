export const MEDIA_FORMAT_PRESETS = ['DVD', 'Blu-ray', 'UHD Blu-ray', 'HD DVD', 'LaserDisc', 'VHS']
export const EDITION_PRESETS = ['Standard Edition', "Collector's Edition", "Director's Cut", 'Extended Edition', 'Limited Edition', 'Steelbook', 'Box Set']
export const CONDITION_PRESETS = ['Sealed', 'Mint', 'Very Good', 'Good', 'Fair', 'Poor']
export const PUBLISHER_PRESETS = ['Warner Bros. Home Entertainment', 'Universal Pictures Home Entertainment', 'Paramount Home Entertainment', 'Sony Pictures Home Entertainment', 'Walt Disney Studios Home Entertainment', '20th Century Studios', 'StudioCanal', 'Lionsgate', 'MGM', 'LEONINE Studios', 'Plaion Pictures', 'Constantin Film', 'Capelight Pictures', 'Turbine Medien', 'Arrow Video', 'The Criterion Collection', 'Shout! Studios', 'Kino Lorber', 'Second Sight Films', '88 Films']
export const LANGUAGE_PRESETS = ['German', 'English', 'French', 'Spanish', 'Italian', 'Portuguese', 'Dutch', 'Danish', 'Swedish', 'Norwegian', 'Finnish', 'Polish', 'Czech', 'Hungarian', 'Turkish', 'Russian', 'Japanese', 'Korean', 'Chinese (Mandarin)', 'Chinese (Cantonese)', 'Arabic']
export const REGION_PRESETS_BY_MEDIA_FORMAT: Record<string, string[]> = {
  DVD: ['Region Free / 0', 'Region 1', 'Region 2', 'Region 3', 'Region 4', 'Region 5', 'Region 6', 'Region 7', 'Region 8'],
  'Blu-ray': ['Region A', 'Region B', 'Region C', 'Region Free'],
  'UHD Blu-ray': ['Region Free'],
  'HD DVD': ['No region coding / Region Free'],
}
