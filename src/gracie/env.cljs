(ns gracie.env
  (:require
   [cljs.pprint :refer [pprint]]
   [cljs-bean.core :refer [->clj]]
   ["dotenv/config"]))

(def ^:private env
  (->> js/process.env
       (js/Object.assign #js {})
       (->clj)))

(defn optional
  [key default]
  (let [value (get env (keyword key) ::not-found)]
    (if (= value ::not-found)
      (do
        (js/console.warn (str "Optional: Could not find ENV var " key))
        default)
      value)))



(defn required
  [key]
  (let [value (get env (keyword key) ::not-found)]
    (if (= value ::not-found)
      (throw (js/Error. (str "Required: Could not find ENV var " key))))
      value))
