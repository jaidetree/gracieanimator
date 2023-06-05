(ns workers.download
  (:require [promesa.core :as p]
            ["path" :as path]
            ["fs" :as fs]
            ["stream" :refer [Readable]]))


(def args
  (-> js/process.argv
      (nth 3)
      (js/JSON.parse)
      (js->clj :keywordize-keys true)))

(defn request->stream
  [request]
  (let [body (.-body request)] (.fromWeb Readable body)))

(defn write-stream
  [src-stream dest]
  (js/Promise. (fn [resolve]
                 (let [dest-stream (.createWriteStream fs dest)]
                   (.once dest-stream
                          "finish"
                          (fn [] (resolve dest))
                          (.pipe src-stream dest-stream))))))


(let [{:keys [src root dir dest]} args]
  (.mkdirSync fs (.join path root dir) #js {:recursive true})
  (p/let [request (js/fetch src)]
    (-> request
        (request->stream)
        (write-stream dest)
        (p/then println)
        (p/catch (fn [err]
                   (js/console.error "Failed downloading" src)
                   (js/console.error err)
                   (js/throw err))))))
