(ns framework.csrf
  (:require
    ["crypto" :as crypto]))

(defn create
  []
  (-> (.randomBytes crypto 32)
      (.toString "hex")))
