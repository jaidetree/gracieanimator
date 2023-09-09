(ns gracie.queue
  (:require
    [clojure.pprint :refer [pprint]]
    [promesa.core :as p]
    ["baconjs" :as bacon]
    [framework.stream :as stream]
    [framework.utils :as u]
    ["fs/promises" :as fs]
    ["path" :as path]))

(def Bus (.-Bus bacon))

(def queue-bus (Bus.))

(defn enqueue
  [action]
  (js/Promise.
    (fn [resolve]
      (.push queue-bus (assoc action :on-complete resolve)))))

(defn request->response
  [{:keys [id fetch reducer] :as request}]
  (p/let [response (fetch)]
    {:response (js->clj response :keywordize-keys true)
     :reducer reducer}))

(defn resource
  [action]
  (let [{:keys [requests on-complete]} action]
    (-> (stream/from-seq requests)
        (.flatMap (fn [request]
                   (stream/from-promise (request->response request))))
        (.reduce {}
                 (fn [ctx {:keys [response reducer]}]
                   (reducer ctx response)))
        (.doAction on-complete)
        (.doError #(js/console.error %)))))

(defn cache
  [{project :data :keys [on-complete] :as action}]
  (let [basename (str (:slug project) ".edn")
        dirname (.join path ".cache" (name (:type project)))
        filepath (.join path dirname basename)
        contents (with-out-str (pprint project))]
   (println "Write to cache" filepath)
   (p/do
     (.mkdir fs dirname #js {:recursive true})
     (.writeFile fs filepath contents #js {:encoding "utf-8"})
     (on-complete filepath))))

(def queue
  (-> queue-bus
      (.flatMapConcat
        (fn [action]
          (case (:type action)
            :resource (resource action)
            :cache    (cache action))))
      (.doError #(js/console.error %))
      (.onValue (fn [_data]
                  nil))))

(comment
  (enqueue
    {:type :resource
     :requests [{:url "https://google.com"
                 :fetch (fn [url]
                          (p/-> (js/fetch url)
                                (.json)))}]
     :on-complete (fn [[json]]
                    (println json))}))

