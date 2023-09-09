(ns framework.cookies
  (:require
    [clojure.string :as s]
    [framework.env :as env]
    ["crypto" :as crypto]))

(defonce private-key (->> :GRACIE_COOKIE_PRIVATE_KEY
                          (env/required)
                          (crypto/createPrivateKey)))

(defn str->buf
  [s & [enc]]
  (js/Buffer.from s (or enc "utf-8")))

(defn buf->hex
  [buf]
  (-> buf
      (.toString "hex")))

(defn buf->utf-8
  [buf]
  (-> buf
      (.toString "utf-8")))

(defn sign
  [data]
  (let [json-buf (-> data
                     (clj->js)
                     (js/JSON.stringify)
                     (str->buf))
        signature (-> (.sign crypto "sha3-224" json-buf private-key)
                      (buf->hex))]
    (str (buf->hex json-buf) "." signature)))

(defn verify
  [signed]
  (let [[json-buf signature] (->> (s/split signed #"\.")
                                  (map #(str->buf % "hex")))
        verified (.verify crypto "sha3-224" json-buf private-key signature)]
    (if verified
      (-> json-buf
          (buf->utf-8)
          (js/JSON.parse)
          (js->clj :keywordize-keys true))
      (do
        (js/console.error "CookieError: Could not verify signature")
        nil))))

(defn serialize-pair
  [[k v]]
  (str k (when v (str "=" v))))

(defn cookie->str
  [cookie]
  (->> cookie
       (keep
         (fn [[kw v]]
           (let [key (name kw)]
            (cond
              (and (boolean? v) (true? v)) [key]
              (boolean? v)                 nil
              :else                        [key v]))))
       (map serialize-pair)
       (s/join ";")))

(defn hash-map->cookie
  [data]
  (let [signed (sign data)
        cookie [[:grace.session signed]
                [:Path "/"]
                [:SameSite "Lax"]
                [:Secure (= js/process.env.NODE_ENV "production")]
                [:HttpOnly true]
                [:MaxAge (* 60 60 24 60)]]]
    (cookie->str cookie)))

(defn str->cookie
  [s]
  (->> (s/split s #";")
       (map #(s/split % #"="))
       (map (fn [[key v]]
              [(keyword key) (cond
                               (nil? v) true
                               (re-matches #"\d+" v) (js/Number v)
                               :else v)]))
       (into {})))

(defn cookie->hash-map
  [cookie-string]
  (let [cookie (str->cookie cookie-string)]
    (verify (get cookie :grace.session))))

(comment
  private-key
  (hash-map->cookie
    {:csrf "random"})
  (let [cookie-str (hash-map->cookie {:csrf "random"})]
    (cookie->hash-map cookie-str)))
