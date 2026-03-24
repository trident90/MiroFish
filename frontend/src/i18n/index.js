import { ref } from 'vue'
import en from './en.json'
import ko from './ko.json'

const messages = { en, ko }
const currentLocale = ref(localStorage.getItem('mirofish_lang') || 'en')

export function useI18n() {
  function t(key) {
    return messages[currentLocale.value]?.[key]
      || messages['en']?.[key]
      || key
  }

  function setLocale(lang) {
    currentLocale.value = lang
    localStorage.setItem('mirofish_lang', lang)
  }

  function getLocale() {
    return currentLocale.value
  }

  return { t, setLocale, getLocale, locale: currentLocale }
}
