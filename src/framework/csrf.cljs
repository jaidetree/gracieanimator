(ns framework.csrf
  (:require
    ["crypto" :as crypto]))

(defn create
  []
  (-> (.randomBytes crypto 16)
      (.toString "hex")))
