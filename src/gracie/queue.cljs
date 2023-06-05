(ns gracie.queue
  (:require
    [promesa.core :as p]
    ["baconjs" :as bacon]))

(def request-cache
  (atom {}))

(def Bus (.-Bus bacon))

(def queue-bus (Bus.))

(defn enqueue
  [action]
  (js/Promise.
    (fn [resolve]
      (.push queue-bus (assoc action :on-complete resolve)))))

(defn cached?
  [url]
  (contains? @request-cache url))

(defn cached
  [url]
  (get @request-cache url))

(defn cache-request
  [url promise]
  (swap! request-cache assoc url promise)
  promise)

(defn do-request
  [{:keys [url fetch]}]
  (if (cached? url)
    (cached url)
    (cache-request url (fetch url))))

(defn resource
  [action]
  (let [{:keys [requests on-complete]} action]
    (println "fetching resource")
    (println requests)
    (-> (.fromPromise
          bacon
          (p/all (map do-request requests))
          true)
        (.map #(js->clj % :keywordize-keys true))
        (.doAction on-complete))))

(defn cache
  [action]
  (println "cache action" action)
  (.once bacon action))

(def queue
  (-> queue-bus
      (.flatMapFirst
        (fn [action]
          (case (:type action)
            :resource (resource action)
            :cache    (cache action))))
      (.doError js/console.error)
      (.onValue println)))

(comment
  (enqueue
    {:type :resource
     :requests [{:url "https://google.com"
                 :fetch (fn [url]
                          (p/-> (js/fetch url)
                                (.json)))}]
     :on-complete (fn [[json]]
                    (println json))}))

