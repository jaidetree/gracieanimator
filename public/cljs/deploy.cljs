(require
  '[clojure.edn :refer [read-string]])

(def bacon js/window.Bacon)

(defn get-element-by-id
  [id]
  (js/document.getElementById id))

(defn bus
  [& [default]]
  (new (.-Bus bacon) default))

(def event-source (js/EventSource. "/deploy/log/"))

(def actions (bus))

(def reducers (atom {}))

(defn defreducer
  [type reducer]
  (swap! reducers assoc type reducer))

(def effects (atom {}))

(defn defeffect
  [type effect]
  (swap! effects assoc type effect))

(defn stream?
  [x]
  (and x (fn? (.-subscribe x))))

(defn promise?
  [x]
  (and x (fn? (.-then x))))

(def state
  (-> actions
      (.scan {}
             (fn [state action]
               (if-let [reducer (get @reducers (:type action))]
                 (reducer state action)
                 state)))
      (.toProperty)))

(defreducer
  :start
  (fn [state {{:keys [total]} :payload}]
    (merge
      state
      {:current  0
       :total    total})))

(defreducer
  :stage
  (fn [state _action]
    (update state :current inc)))

(defn update-status
  [text]
  (when (string? text)
   (let [status (get-element-by-id "status")]
     (set! (.-innerText status) text))))

(defeffect
  :start
  (fn [_state action]
    (let [progress-bar (get-element-by-id "progress-bar")
          spinner (get-element-by-id "spinner")]
      (.. spinner -classList (add "hidden"))
      (.. progress-bar -classList (remove "hidden"))
      (update-status (get-in action [:payload :status])))))

(defeffect
  :stage
  (fn [state _action]
    (let [width (* (/ (:current state) (:total state)) 100)
          progress (get-element-by-id "progress")]
      (set! (.. progress -style -width) (str width "%")))))

(defeffect
  :end
  (fn [_state _action]
    (.close event-source)))

(defeffect
  :complete
  (fn [_state action]
    (.close event-source)
    (update-status (get-in action [:payload :status]))
    (-> (.interval bacon 1000 1)
        (.scan 5 -)
        (.takeWhile pos?)
        (.map (fn [seconds]
                (let [msg (get-in action [:payload :status])
                      suffix (if (= seconds 1)
                              "1 second"
                              (str seconds " seconds"))]
                  (.replace msg "5 seconds" suffix))))

        (.doAction update-status)
        (.doEnd
         (fn []
           (set! (.-pathname js/window.location) "/")))
        (.doError js/console.error))))

(defeffect
  :status
  (fn [_state action]
    (update-status (get action :payload))))

(defn subscribe
  [source bus]
  (.subscribe source
              (fn [event]
                (cond (.-isEnd event)   (.end bus)
                      (.-isError event) (.push bus (.-value event))
                      :else             (.push bus (.-value event))))))

(-> state
   (.combine actions vector)
   (.flatMap
     (fn [[state action]]
       (if-let [effect (get @effects (:type action))]
         (let [result (effect state action)]
           (cond (stream? result)  result
                 (promise? result) (.fromPromise bacon result)
                 (map? result)     (.once bacon result)
                 (vector? result)  (.fromArray (clj->js result))
                 (nil? result)     (.never bacon)
                 :else             (do
                                     (println "Unknown effect return type" result)
                                     (.never bacon))))
         (.never bacon))))
   (subscribe actions))

#_(-> state
      (.doError prn)
      (.onValue prn))

(defn format-message
  [action]
  (prn-str action))

(defn log-msg
  [msg-str]
  (let [el (get-element-by-id "log")
        text (js/document.createTextNode msg-str)
        scroll-height (.-scrollHeight el)]
   (.appendChild el text)
   (set! (.-scrollTop el) scroll-height)))

(-> actions
    (.map format-message)
    (.onValue log-msg))

(-> (.fromEvent bacon event-source "message")
    (.map #(.-data %))
    (.map read-string)
    (.map #(assoc % :source :server))
    (.doError (fn [error]
                (.close event-source)
                (js/console.error (.-message error))))
    (subscribe actions))

(-> (.fromEvent bacon event-source "error")
    (.onValue js/console.error))
